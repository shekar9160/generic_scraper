A crawler
=========

A crawler to collect all components together:

* splash with HH scripts

TODO:

* autologin + autoregister + login keychain
* crazy-form-submitter
* captcha solving
* pagination


Installation
------------

Requires Python 3.4:

    pip install -r requirements.lock.txt
    python -c "import formasaurus; formasaurus.extract_forms('a')"


Run crawler
-----------

Start splash:

    docker run -p 8050:8050 scrapinghub/splash

Specify url to crawl via the ``url`` param, and run the ``autologin`` spider:

    scrapy crawl autologin -a url=http://127.0.0.1:8001

You can also specify a file to read urls from, with ``-a url=./urls.txt'``.
Useful options to tweak (add to the above command via ``-s NAME=value``):

- ``SPLASH_URL`` url of the splash instance
- ``DOWNLOAD_DELAY`` - set to 0 when crawling local test server
- ``RUN_HH`` - set to 0 to skip running full headless-horesman scripts


Run login keychain UI
---------------------

    python undercrawler/login_keychain_ui.py --debug

And visit http://127.0.0.1:5000/. SQLite is used as a database,
it is stored at ``undercrawler/keychain_db.sqlite`` and created if missing
on the UI app start.
