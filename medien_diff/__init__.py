import os

import tweepy
import rq
import sentry_sdk
import click
import flask
import flask_admin
import flask_admin.contrib.sqla
from sqlalchemy import Index
from sqlalchemy.exc import ProgrammingError
from redis import Redis
from rq import Queue

from medien_diff.models import init_db, Newspaper, ArticleRevision


app = flask.Flask(__name__)
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]

sentry_sdk.init(
    _experiments={"auto_enabling_integrations": True},
    traces_sample_rate=1.0,
    environment=app.env,
    in_app_include=["medien_diff"],
)


# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["SQLALCHEMY_DATABASE_URI"]
db = init_db(app)

# XXX: Honor envvar
redis_conn = Redis()


class ResultlessQueue(Queue):
    def enqueue(*args, **kwargs):
        kwargs.setdefault("result_ttl", 0)
        kwargs.setdefault("failure_ttl", 0)
        Queue.enqueue(*args, **kwargs)


QUEUES = {
    "main": ResultlessQueue("medien_diff_main", connection=redis_conn),
    "slow": ResultlessQueue("medien_diff_slow", connection=redis_conn),
    "twitter": Queue("medien_diff_twitter", connection=redis_conn),
}

redis_queue_main = QUEUES["main"]

# VIEWS
class ModelView(flask_admin.contrib.sqla.ModelView):
    def __init__(self, model, *args, with_primary_key=False, **kwargs):
        if with_primary_key:
            self.column_list = [c.key for c in model.__table__.columns]
            self.form_columns = self.column_list

        if hasattr(model, "form_create_rules"):
            self.form_create_rules = model.form_create_rules

        super(ModelView, self).__init__(model, *args, **kwargs)


admin = flask_admin.Admin(app)
admin.add_view(ModelView(Newspaper, db.session))
admin.add_view(ModelView(ArticleRevision, db.session, with_primary_key=True))


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.cli.command()
@click.option("--run-worker/--no-run-worker", default=True)
def refresh(run_worker):
    from medien_diff.tasks import refresh_all

    redis_queue_main.enqueue(refresh_all)

    if run_worker:
        worker = rq.SimpleWorker(list(QUEUES.values()), connection=redis_conn)
        worker.work(burst=True)


@app.cli.command()
def twitter():
    paper = db.session.query(Newspaper).get(int(click.prompt("ID of newspaper")))
    if (
        paper.twitter_consumer_key
        or paper.twitter_consumer_secret
        or paper.twitter_access_token_key
        or paper.twitter_access_token_secret
    ):
        click.echo("Credentials already exist, clear them out first!")
        click.exit(1)

    consumer_key = click.prompt("Consumer key")
    consumer_secret = click.prompt("Consumer secret")

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)

    click.echo("Go to {}".format(auth.get_authorization_url()))

    access_token_key, access_token_secret = auth.get_access_token(
        click.prompt("Verification code")
    )
    paper.twitter_consumer_key = consumer_key
    paper.twitter_consumer_secret = consumer_secret
    paper.twitter_access_token_key = access_token_key
    paper.twitter_access_token_secret = access_token_secret
    db.session.commit()
