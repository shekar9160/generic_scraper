Undercrawler
============

[![Build Status](https://travis-ci.org/TeamHG-Memex/undercrawler.svg?branch=master)](https://travis-ci.org/TeamHG-Memex/undercrawler)
[![codecov.io](https://codecov.io/github/TeamHG-Memex/undercrawler/coverage.svg?branch=master)](https://codecov.io/github/TeamHG-Memex/undercrawler?branch=master)

This is a generic scrapy crawler. It is designed to handle a number
of challenges that are hard for traditional generic crawlers, such as
dynamic content, login and search forms, pagination. It crawls from the given
seed url in breadth first order,
exporting all carwled pages and documents into the CDRv2 format.

License is MIT.

Main features and used components are:

- All pages are downloaded using [Splash2](https://github.com/scrapinghub/splash),
  which is a lightweight web browser with an HTTP API.
  [Aquarium](https://github.com/TeamHG-Memex/aquarium) can be used to
  adds a load balancer for multiple Splash processes,
  compression for HTTP responses, Tor support (automatic for .onion links) and
  AdBlock Plus filters support.
- Headless Horseman Scripts help to reveal dynamic content
  such as infinite scrolls, removing overlays,
  elements revealed by clicking, etc.
  They are implemented as JS scripts that are injected into each rendered page,
  and Lua scripts that control the Splash browser.
- [Autologin](https://github.com/TeamHG-Memex/autologin) service is used:
  it includes a UI for managing login credentials and a service that logs in
  and hands cookies to the crawler.
  It also includes a spider that finds login and registration forms
  to aid manual registration.
- [Autopager](https://github.com/TeamHG-Memex/autopager) is used to detect
  pagination links. It allows the crawler to reach content via pagination
  faster and without hitting the depth limit,
  and to stay within the given soft "domain":
  if we start from a page with a paginator,
  we will crawl all the pages first before going elsewhere.
- Crazy Form Submitter discovers new content by performing searches.
  It uses predefined search terms (letters, digits and symbols) as well as
  user-supplied terms, and tries random refinements using checkbox controls.
- Links are additionally extracted links from iframes and onclick handlers.
- The crawler tries to avoid duplicate content by learning which URL
  components do not alter the contents of the page, using MinHash LSH
  for duplicate detection.
- [Formasaurus](https://github.com/TeamHG-Memex/Formasaurus) is a library
  for form and field classification that is used by AutoLogin and
  Crazy Form Submitter.

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

Start splash (or use [Aquarium](https://github.com/TeamHG-Memex/aquarium)):

    docker run -p 8050:8050 scrapinghub/splash

Start [Autologin](https://github.com/TeamHG-Memex/autologin) HTTP API
with the ``autologin-http-api`` command,
and the UI server with ``autologin-server``.

Specify url to crawl via the ``url`` param, and run the ``base`` spider:

    scrapy crawl base -a url=http://127.0.0.1:8001

You can also specify a file to read urls from, with ``-a url=./urls.txt``,
but in this case you must disable autologin with ``-s AUTOLOGIN_ENABLED=0``,
or ensure that all urls use common authentication.

Useful options to tweak (add to the above command via ``-s NAME=value``):

- ``ADBLOCK`` - set to 1 to enable AdBlock filters (they can make crawling faster)
- ``AUTOLOGIN_ENABLED`` - set to 0 to disable autologin middleware
- ``AUTOLOGIN_URL`` - url of the autologin HTTP API
- ``CDR_CRAWLER``, ``CDR_TEAM`` - CDR export metadata constants
- ``CRAZY_SEARCH_ENABLED`` - set to 0 to disable submitting search forms
- ``DOWNLOAD_DELAY`` - set to 0 when crawling local test server
- ``FILES_STORE`` - S3 location for saving extracted documents
  (format is ``s3://bucket/prefix/``)
- ``FORCE_TOR`` - crawl via tor to avoid blocking
- ``HARD_URL_CONSTRAINT`` - set to 1 to treat start urls as hard constraints
  (by default we start from given url but crawl the whole domain)
- ``MAX_DOMAIN_SEARCH_FORMS`` - max number of search forms considered for domain
- ``PREFER_PAGINATION`` - set to 0 to disable pagination handling, or adjust
  as needed (value is in seconds).
- ``RUN_HH`` - set to 0 to skip running full headless-horesman scripts
- ``SEARCH_TERMS_FILE`` - file with extra search terms to use (one per line)
- ``SPLASH_URL`` - url of the splash instance
- ``USERNAME``, ``PASSWORD``, ``LOGIN_URL`` - specify values to pass to
  autologin - use them if you do not want to use autologin keychain UI.
  ``LOGIN_URL`` is a relative url.

Pages are stored in CDRv2 format, with the following custom fields inside
``extracted_metadata``:

- ``depth``: page depth
- ``extracted_at``: a page where this link was (first) extracted
- ``form``: forms metadata extracted by formasaurus
- ``from_search``: page was reached from search results
- ``is_iframe``: page url was extracted from an ``iframe``
- ``is_onclick``: page url was extracted from ``onclick``, not from a normal link
- ``is_page``: page was reached via pagination
- ``is_search``: this is a search result page

All documents (including images) are exported if ``FILES_STORE`` is set.

You can use ``./scripts/crawl_stats.py`` to analyze extracted metadata.

Scripts
-------

* ``./scripts/crawl_stats.py``:
  show crawling stats, including ``extracted_metadata``
* ``./scripts/gen_supervisor_configs.py``:
  generate supervisord configs for crawlers from a list of urls

Tests
-----

Run all tests with:

    tox

This assumes that splash is running on the default url http://127.0.0.1:8050,
you can pass it to tests like this (required on OS X with splash in docker):

    SPLASH_URL=http://192.168.99.100:8050 tox

Note that you can not use an external splash instance, because tests start
local test servers.

Tests are run using py.test, you can pass arguments after ``--``:

    tox -- tests/test_spider.py
