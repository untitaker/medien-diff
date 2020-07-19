# medien-diff

A small command-line tool and web application that scrapes news websites for headlines and posts any changes to Twitter. It works exactly like [nyt-diff](https://github.com/j-e-d/NYTdiff). The main difference to nyt-diff is that which websites to scrape (and how to scrape them) is user-configurable via web interface.

## Installation

1. Install `chromedriver` (Homebrew has a package for that, as do other package managers)
2. Install Postgres and create a database called `medien_diff`.
3. Install Python 3, preferrably via pyenv (see `.python-version`)
4. Install [poetry](https://python-poetry.org/)
5. Run `poetry install`
6. Run `make upgradedb` to create tables.

## Setting up newspapers

1. Run `make server` to launch a webserver. You should absolutely not expose this to the outside world, as it has no auth.
2. Go to `http://127.0.0.1:5000/admin` to view your entire database, and add or remove newspapers.

## Refreshing

1. Run `make refresh` to spawn a refresh job. You will need to run this regularly, in a cronjob of some sort, to keep your Twitter account active.
2. Run `make worker` to run an additional process to help the previous process with downloading and processing.
3. Run `make server` and go to `http://127.0.0.1:5000/queues` to view pending and failed jobs. If sending a tweet fails, you have the option to retry it or delete it. All other job failures are discarded immediately.

## Crash reporting

1. Sign up for [Sentry](sentry.io/), and create a project.
2. Set the `MEDIEN_DIFF_SENTRY_DSN` to the DSN you received, or pass it into the `Makefile` like `make SENTRY_DSN=... refresh`

## License

Licensed under the BSD license, see [`LICENSE`](./LICENSE).
