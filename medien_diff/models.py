from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from flask_admin.form import rules

db = SQLAlchemy()
migrate = Migrate()


def init_db(app):
    db.init_app(app)
    migrate.init_app(app, db)
    return db


class Newspaper(db.Model):
    __tablename__ = "newspaper"

    form_create_rules = form_edit_rules = (
        rules.HTML("<p>Name of the newspaper. For example: <code>Der Standard</code>"),
        "name",
        rules.HTML(
            "<p>URL of the frontpage or some other page where all the articles are linked. For example: <code>https://www.derstandard.at/frontpage/latest</code>"
        ),
        "base_url",
        rules.HTML(
            "<p>Regex that matches against article URLs. For example: <code>^https://www.derstandard.at/story/</code>"
        ),
        "article_url_pattern",
        rules.HTML(
            "<p>CSS selector that matches the title text when viewing the article page. For example: <code>.article-title</code>"
        ),
        "article_title_css_selector",
        rules.HTML(
            "<p>Twitter credentials to use to post to Twitter. Consumer = Twitter app, Access token = Login into an account. Use <code>make twitter</code> to generate the latter."
        ),
        "twitter_consumer_key",
        "twitter_consumer_secret",
        "twitter_access_token_key",
        "twitter_access_token_secret",
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    base_url = db.Column(db.String)
    article_url_pattern = db.Column(db.String)

    article_title_css_selector = db.Column(db.String)

    twitter_consumer_key = db.Column(db.String)
    twitter_consumer_secret = db.Column(db.String)
    twitter_access_token_key = db.Column(db.String)
    twitter_access_token_secret = db.Column(db.String)


class ArticleRevision(db.Model):
    __tablename__ = "article_revision"

    newspaper = db.Column(db.Integer, db.ForeignKey("newspaper.id"))
    url = db.Column(db.String, primary_key=True)
    fetched_at = db.Column(db.DateTime)
    changed_at = db.Column(db.DateTime, index=True)

    title = db.Column(db.String)
