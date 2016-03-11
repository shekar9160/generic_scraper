A crawler
=========

A crawler to collect all components together:

* splash with HH scripts
* autologin + login keychain

TODO:

* autoregister
* crazy-form-submitter
* captcha solving
* pagination


Installation
------------

Requires Python 3.4:

    pip install -r requirements.txt
    python -c "import formasaurus; formasaurus.extract_forms('a')"

You also will need splash (but you can just use docker, see below),
and install autologin separately (https://github.com/TeamHG-Memex/autologin),
from the branch crawler-integration.

Run crawler
-----------

Start splash:

    docker run -p 8050:8050 scrapinghub/splash

Start autologin HTTP API with the ``autologin-http-api`` command,
and the UI server with ``autologin-server``.

Specify url to crawl via the ``url`` param, and run the ``base`` spider:

    scrapy crawl base -a url=http://127.0.0.1:8001

Useful options to tweak (add to the above command via ``-s NAME=value``):

- ``SPLASH_URL`` url of the splash instance
- ``AUTOLOGIN_URL`` url of the autologin HTTP API
- ``DOWNLOAD_DELAY`` - set to 0 when crawling local test server
- ``RUN_HH`` - set to 0 to skip running full headless-horesman scripts
