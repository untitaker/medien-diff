import re
import io
import logging
import datetime
import hashlib
import urllib
import functools
import random
import tempfile

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import flask
import difflib
import tweepy
import simplediff

import sentry_sdk

import lxml.html
import lxml.etree

import requests

from medien_diff import QUEUES, redis_conn
from medien_diff.models import db, Newspaper, ArticleRevision
from medien_diff.html_utils import css, to_string
from medien_diff.text import is_significant_title_change
from medien_diff.sentry_utils import tag_http_response

http_session = requests.session()
requests.utils.add_dict_to_cookiejar(
    http_session.cookies, {"DSGVO_ZUSAGE_V1": "true",}  # derstandard needs this
)

_ALL_LINKS_XPATH = css("a")

logger = logging.Logger(__name__)


class MissingData(Exception):
    pass


def job(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        from medien_diff import app

        with app.app_context():
            return f(*args, **kwargs)

    return inner


@job
def refresh_all():
    for paper in db.session.query(Newspaper).all():
        QUEUES["main"].enqueue(fetch_newspaper_frontpage, newspaper_id=paper.id)

    now = datetime.datetime.now()

    articles = list(
        db.session.query(ArticleRevision).filter(
            ArticleRevision.fetched_at < now - datetime.timedelta(days=7)
        )
    )

    random.shuffle(articles)

    for article in articles:
        QUEUES["slow"].enqueue(
            fetch_newspaper_article,
            newspaper_id=article.newspaper,
            url=article.url,
            delete_if_no_change=True,
            delete_if_no_match_regex=True,
        )


@job
def fetch_newspaper_frontpage(newspaper_id):
    sentry_sdk.set_tag("newspaper_id", newspaper_id)

    paper = db.session.query(Newspaper).get(newspaper_id)

    article_url_pattern = re.compile(paper.article_url_pattern)

    response = http_session.get(paper.base_url)
    tag_http_response(response)
    response.raise_for_status()

    tree = lxml.html.fromstring(response.text)

    links = list(tree.xpath(_ALL_LINKS_XPATH))
    found = False

    for link in links:
        href = link.attrib.get("href", "").strip()
        if not href:
            continue

        href = urllib.parse.urljoin(response.url, href)
        href = href.split("?")[0]
        href = href.split("#")[0]

        if article_url_pattern.match(href):
            found = True
            QUEUES["main"].enqueue(
                fetch_newspaper_article, newspaper_id=newspaper_id, url=href
            )

    if not found:
        raise MissingData("frontpage.empty")


@job
def fetch_newspaper_article(
    newspaper_id, url, delete_if_no_change=False, delete_if_no_match_regex=False
):
    sentry_sdk.set_tag("newspaper_id", newspaper_id)
    sentry_sdk.set_tag("url", url)
    now = datetime.datetime.now()

    paper = db.session.query(Newspaper).get(newspaper_id)

    if delete_if_no_match_regex and not re.compile(paper.article_url_pattern).match(
        url
    ):
        db.session.query(ArticleRevision).filter(ArticleRevision.url == url).delete()
        return

    response = http_session.get(url)
    tag_http_response(response)
    response.raise_for_status()

    article = db.session.query(ArticleRevision).get(response.url)
    if article is None:
        article = db.session.query(ArticleRevision).get(url)
        if article is not None:
            article.url = response.url
    else:
        db.session.query(ArticleRevision).filter(ArticleRevision.url == url).delete()

    tree = lxml.html.fromstring(response.text)

    title_iter = list(tree.xpath(css(paper.article_title_css_selector)))

    if len(title_iter) < 1:
        raise MissingData("article.title.zero")
    elif len(title_iter) != 1:
        logger.error("article.title.not_one", extra={"titles": title_iter})

    title = to_string(title_iter[0])

    if article is None:
        article = ArticleRevision(
            newspaper=newspaper_id,
            url=url,
            title=title,
            fetched_at=now,
            changed_at=now,
        )
        db.session.add(article)
    else:
        assert article.newspaper == newspaper_id
        changed = False

        if is_significant_title_change(article.title, title):
            QUEUES["twitter"].enqueue(
                tweet, newspaper_id=newspaper_id, url=url, old=article.title, new=title
            )
            article.title = title
            changed = True

        article.fetched_at = now

        if changed:
            article.changed_at = now

        if not changed and delete_if_no_change:
            db.session.delete(article)

    db.session.commit()


@job
def tweet(newspaper_id, url, old, new):
    paper = db.session.query(Newspaper).get(newspaper_id)

    if (
        not paper.twitter_consumer_key
        or not paper.twitter_consumer_secret
        or not paper.twitter_access_token_key
        or not paper.twitter_access_token_secret
    ):
        return

    # Defend against broken db entries
    hasher = hashlib.sha256()
    hasher.update(str(newspaper_id).encode("ascii"))
    hasher.update(b":")
    hasher.update(url.encode("utf8"))
    hasher.update(b":")
    hasher.update(old.encode("utf8"))
    hasher.update(b":")
    hasher.update(new.encode("utf8"))
    debounce_key = hasher.hexdigest()

    if redis_conn.get(debounce_key):
        logger.error("tweet.duplicate")
        return

    redis_conn.set(debounce_key, b"1")

    html_ctx = tempfile.NamedTemporaryFile(suffix=".html")
    png_ctx = tempfile.NamedTemporaryFile(suffix=".png")

    with html_ctx as f, png_ctx as png:
        f.write(b'<meta charset="utf-8">')
        f.write(
            '<link rel="stylesheet" href="file://{css_path}/diff.css">'.format(
                css_path=flask.current_app.static_folder
            ).encode("utf8")
        )
        f.write(b"<body><p>")
        f.write(simplediff.html_diff(old, new).encode("utf8"))
        f.write(b"</p></body>")
        f.flush()

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(chrome_options=chrome_options)
        driver.get("file://{}".format(f.name))
        driver.find_element_by_tag_name("p").screenshot(png.name)

        auth = tweepy.OAuthHandler(
            paper.twitter_consumer_key, paper.twitter_consumer_secret
        )
        auth.set_access_token(
            paper.twitter_access_token_key, paper.twitter_access_token_secret
        )
        api = tweepy.API(auth)

        # Passing a fileobject into tweepy actually does not work, despite what the
        # documentation suggests.
        media_id = api.media_upload(png.name).media_id_string

    api.update_status(status=url, media_ids=[media_id])
