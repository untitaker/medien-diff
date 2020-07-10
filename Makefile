export FLASK_APP := medien_diff:app
export FLASK_SECRET_KEY := 5C97DD8C-24EF-4B59-BAC5-FDDC798A0D58
export SENTRY_DSN := $(MEDIEN_DIFF_SENTRY_DSN)
export FLASK_ENV := development
export SQLALCHEMY_DATABASE_URI := postgresql+psycopg2://postgres:postgres@localhost/medien_diff
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY := YES

shell:
	$(SHELL)

server:
	poetry run flask run

worker:
	poetry run rq worker -c medien_diff --sentry-dsn="" medien_diff_main medien_diff_slow medien_diff_twitter

refresh:
	poetry run flask refresh

queues:
	poetry run rq-dashboard

format:
	poetry run black .

# Create a migration
migratedb:
	poetry run flask db migrate

# Run migrations
upgradedb:
	poetry run flask db upgrade

twitter:
	poetry run flask twitter

test:
	poetry run pytest tests
