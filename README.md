A crawler
=========

A crawler to collect all components together.

TODO:

* splash with HH scripts
* autologin + autoregister + login keychain
* crazy-form-submitter
* captcha solving
* pagination


Installation
------------

Requires Python 3.4:

    pip install -r requirements.lock.txt


Run crawler
-----------

Start splash:

    docker run -p 8050:8050 scrapinghub/splash

Set ``SPLASH_URL`` in ``undercrawler/local_settings.py`` if different
from the default in ``undercrawler/settings.py``.

Specify url to crawl via the ``url`` param
(``DOWNLOAD_DELAY`` set to 0 here as this is a local test server):

    scrapy crawl crawler -a url=http://192.168.1.41:8001 -s DOWNLOAD_DELAY=0
