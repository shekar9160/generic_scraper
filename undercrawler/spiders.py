from base64 import b64decode
import codecs
import contextlib
import hashlib
import os
import re
from typing import Optional
from urllib.parse import urljoin, urlsplit
import uuid

import autopager
import formasaurus
import scrapy
from scrapy import Request, FormRequest
from scrapy.linkextractors import LinkExtractor
from scrapy.settings import Settings
from scrapy.utils.url import canonicalize_url, add_http_if_no_scheme
from scrapy.utils.python import unique
from scrapy_cdr import text_cdr_item
from scrapy_splash import SplashRequest, SplashFormRequest
from autologin_middleware import link_looks_like_logout

from .crazy_form_submitter import search_form_requests
from .utils import cached_property, extract_text, load_directive, using_splash
import undercrawler.settings


class BaseSpider(scrapy.Spider):
    name = 'undercrawler'

    def __init__(self, url, search_terms=None, *args, **kwargs):
        if url.startswith('.'):
            with codecs.open(url, 'r', encoding='utf8') as f:
                urls = [line.strip() for line in f]
        else:
            urls = [url]
        self.start_urls = [add_http_if_no_scheme(_url) for _url in urls]
        self.search_terms = search_terms
        self._extra_search_terms = None  # lazy-loaded via extra_search_terms
        self._reset_link_extractors()
        self.images_link_extractor = LinkExtractor(
            tags=['img'], attrs=['src'], deny_extensions=[],
            canonicalize=False)
        self.state = {}
        self.use_splash = None  # set up in start_requests
        self._screenshot_dest = None  # set up in _take_screenshot
        # Load headless horseman scripts
        self.lua_source = load_directive('headless_horseman.lua')
        self.js_source = load_directive('headless_horseman.js')
        super().__init__(*args, **kwargs)

    def start_requests(self):
        self.use_splash = using_splash(self.settings)
        for url in self.start_urls:
            yield self.make_request(url, callback=self.parse_first)

    def make_request(
            self, url, callback=None, meta=None, cls=None, **kwargs):
        callback = callback or self.parse
        cls = cls or (SplashRequest if self.use_splash else Request)
        if self.use_splash:
            settings = self.settings
            splash_args = {
                'lua_source': self.lua_source,
                'js_source': self.js_source,
                'run_hh': settings.getbool('RUN_HH'),
                'return_png': settings.getbool('SCREENSHOT'),
                'images_enabled': settings.getbool('IMAGES_ENABLED'),
            }
            for s in ['VIEWPORT_WIDTH', 'VIEWPORT_HEIGHT',
                      'SCREENSHOT_WIDTH', 'SCREENSHOT_HEIGHT']:
                if self.settings.get(s):
                    splash_args[s.lower()] = self.settings.getint(s)
            if self.settings.getbool('ADBLOCK'):
                splash_args['filters'] = 'fanboy-annoyance,easylist'
            if self.settings.getbool('FORCE_TOR'):
                splash_args['proxy'] = 'tor'
            kwargs.update(dict(
                args=splash_args,
                endpoint='execute',
                cache_args=['lua_source', 'js_source'],
            ))
        meta = meta or {}
        meta['avoid_dup_content'] = True
        return cls(url, callback=callback, meta=meta, **kwargs)

    def parse_first(self, response):
        self.allowed += (allowed_re(
            response.url, self.settings.getbool('HARD_URL_CONSTRAINT')),)
        self.logger.info('Updated allowed regexps: %s', self.allowed)
        yield from self.parse(response)

    def parse(self, response):
        if not self.link_extractor.matches(response.url):
            return

        request_meta = {
            'from_search': response.meta.get('is_search'),
            'extracted_at': response.url,
        }

        def request(url, meta=None, **kwargs):
            meta = meta or {}
            meta.update(request_meta)
            return self.make_request(url, meta=meta, **kwargs)

        forms = (formasaurus.extract_forms(response.text) if response.text
                 else [])
        metadata = dict(
            is_page=response.meta.get('is_page', False),
            is_onclick=response.meta.get('is_onclick', False),
            is_iframe=response.meta.get('is_iframe', False),
            is_search=response.meta.get('is_search', False),
            from_search=response.meta.get('from_search', False),
            extracted_at=response.meta.get('extracted_at', None),
            depth=response.meta.get('depth', None),
            priority=response.request.priority,
            forms=[meta for _, meta in forms],
            screenshot=self._take_screenshot(response),
        )
        follow_urls = {link_to_url(link) for link in
                       self.link_extractor.extract_links(response)
                       if not self._looks_like_logout(link, response)}
        yield self.text_cdr_item(
            response, follow_urls=follow_urls, metadata=metadata)

        if self.settings.getbool('PREFER_PAGINATION'):
            # Follow pagination links; pagination is not a subject of
            # a max depth limit. This also prioritizes pagination links because
            # depth is not increased for them.
            with _dont_increase_depth(response):
                for url in self._pagination_urls(response):
                    # self.logger.debug('Pagination link found: %s', url)
                    yield request(url, meta={'is_page': True})

        # Follow all in-domain links.
        # Pagination requests are sent twice, but we don't care because
        # they're be filtered out by a dupefilter.
        for url in follow_urls:
            yield request(url)

        # urls extracted from onclick handlers
        for url in get_js_links(response):
            priority = 0 if _looks_like_url(url) else -15
            url = response.urljoin(url)
            yield request(url, meta={'is_onclick': True}, priority=priority)

        # go to iframes
        for link in self.iframe_link_extractor.extract_links(response):
            yield request(link_to_url(link), meta={'is_iframe': True})

        # Try submitting forms
        for form, meta in forms:
            for request_kwargs in self.handle_form(response.url, form, meta):
                yield request(**request_kwargs)

    def handle_form(self, url, form, meta):
        action = canonicalize_url(urljoin(url, form.action))
        if not self.link_extractor.matches(action):
            return
        if (meta['form'] == 'search' and
                self.settings.getbool('CRAZY_SEARCH_ENABLED') and
                action not in self.handled_search_forms and
                len(self.handled_search_forms) <
                self.settings.getint('MAX_DOMAIN_SEARCH_FORMS')):
            self.logger.debug('Found a search form at %s', url)
            self.handled_search_forms.add(action)
            for request_kwargs in search_form_requests(
                    url, form, meta,
                    search_terms=self.search_terms,
                    extra_search_terms=self.extra_search_terms):
                request_kwargs['meta'] = {'is_search': True}
                request_kwargs['cls'] = \
                    SplashFormRequest if self.use_splash else FormRequest
                yield request_kwargs

    def media_urls(self, response, follow_urls):
        """ Return all links to media objects (urls).
        """
        urls = set()
        for extractor in [
                self.images_link_extractor, self.files_link_extractor]:
            urls.update(
                link_to_url(link) for link in extractor.extract_links(response)
                if not self._looks_like_logout(link, response))
        urls.difference_update(follow_urls)
        return urls

    def text_cdr_item(self, response, *, follow_urls, metadata):
        if self.settings.get('FILES_STORE'):
            media_urls = self.media_urls(response, follow_urls)
        else:
            media_urls = []
        return text_cdr_item(
            response,
            crawler_name=self.settings.get('CDR_CRAWLER'),
            team_name=self.settings.get('CDR_TEAM'),
            # will be downloaded by UndercrawlerMediaPipeline
            objects=media_urls,
            metadata=metadata,
        )

    def _pagination_urls(self, response):
        return [
            url for url in
            unique(
                canonicalize_url(url, keep_fragments=True)
                for url in autopager.urls(response)
            )
            if self.link_extractor.matches(url)
            ]

    @cached_property('_extra_search_terms')
    def extra_search_terms(self):
        st_file = self.settings.get('SEARCH_TERMS_FILE')
        if st_file:
            with codecs.open(st_file, 'r', encoding='utf8') as f:
                return [line.strip() for line in f]
        else:
            return []

    @property
    def allowed(self):
        return self.state.setdefault('allowed', ())

    @allowed.setter
    def allowed(self, allowed):
        self.state['allowed'] = allowed
        # Reset link extractors to pick up with the latest self.allowed regexps
        self._reset_link_extractors()

    def _reset_link_extractors(self):
        self._link_extractor = None
        self._files_link_extractor = None
        self._iframe_link_extractor = None

    @cached_property('_link_extractor')
    def link_extractor(self):
        return LinkExtractor(allow=self.allowed, unique=False,
                             canonicalize=False)

    @cached_property('_iframe_link_extractor')
    def iframe_link_extractor(self):
        return LinkExtractor(
            allow=self.allowed, tags=['iframe'], attrs=['src'],
            unique=False, canonicalize=False)

    @cached_property('_files_link_extractor')
    def files_link_extractor(self):
        return LinkExtractor(
            allow=self.allowed,
            tags=['a'],
            attrs=['href'],
            deny_extensions=[],  # allow all extensions
            canonicalize=False,
        )

    @property
    def handled_search_forms(self):
        return self.state.setdefault('handled_search_forms', set())

    def _looks_like_logout(self, link, response):
        if not self.settings.getbool('AUTOLOGIN_ENABLED') or not \
                response.meta.get('autologin_active'):
            return False
        return link_looks_like_logout(link)

    def _take_screenshot(self, response) -> Optional[str]:
        screenshot = response.data.get('png') if self.use_splash else None
        if not screenshot:
            return None
        if self._screenshot_dest is None:
            self._screenshot_dest = (
                self.settings.get('SCREENSHOT_DEST', 'screenshots'))
            if not os.path.exists(self._screenshot_dest):
                os.mkdir(self._screenshot_dest)
        filename = os.path.join(
            self._screenshot_dest,
            '{prefix}{uuid}.png'.format(
                prefix=self.settings.get('SCREENSHOT_PREFIX', ''),
                uuid=uuid.uuid4()))
        with open(filename, 'wb') as f:
            f.write(b64decode(screenshot))
        self.logger.debug('Saved %s screenshot to %s' % (response, filename))
        return filename


class ArachnadoSpider(BaseSpider):
    name = 'undercrawler_arachnado'
    custom_settings = Settings()
    custom_settings.setmodule(undercrawler.settings)
    custom_settings['ITEM_PIPELINES'][
        'arachnado.pipelines.mongoexport.MongoExportPipeline'] = 600
    custom_settings.update({
        # Convenient to have defaults for all crawls
        'SPLASH_URL': os.environ.get('SPLASH_URL'),
        'FILES_STORE': os.environ.get('FILES_STORE'),
        # Override some undesired Arachnado settings
        'AUTOTHROTTLE_ENABLED': False,
        'DOWNLOAD_MAXSIZE': None,
    })

    def __init__(self, *, domain, crawl_id):
        self.crawl_id = crawl_id
        self.domain = domain
        super().__init__(url=domain)
        self.start_url = self.start_urls[0]


@contextlib.contextmanager
def _dont_increase_depth(response):
    # XXX: a hack to keep the same depth for outgoing requests
    response.meta['depth'] -= 1
    try:
        yield
    finally:
        response.meta['depth'] += 1


_onclick_search = re.compile("(?P<sep>('|\"))(?P<url>.+?)(?P=sep)").search


def get_onclick_url(attr_value):
    """
    >>> get_onclick_url("window.open('page.html?productid=23','win2')")
    'page.html?productid=23'
    >>> get_onclick_url("window.location.href='http://www.jungleberry.co.uk/Fair-Trade-Earrings/Aguas-Earrings.htm'")
    'http://www.jungleberry.co.uk/Fair-Trade-Earrings/Aguas-Earrings.htm'
    """
    m = _onclick_search(attr_value)
    return m.group("url").strip() if m else m


def get_js_links(response):
    """ Extract URLs from JS. """
    urls = [
        get_onclick_url(value)
        for value in response.xpath('//*/@onclick').extract()
        ]
    # TODO: extract all URLs from <script> tags as well?
    return [url for url in urls if url]


def _looks_like_url(txt):
    """
    Return True if text looks like an URL (probably relative).
    >>> _looks_like_url("foo.bar")
    False
    >>> _looks_like_url("http://example.com")
    True
    >>> _looks_like_url("/page2")
    True
    >>> _looks_like_url("index.html")
    True
    >>> _looks_like_url("foo?page=1")
    True
    >>> _looks_like_url("x='what?'")
    False
    >>> _looks_like_url("visit this page?")
    False
    >>> _looks_like_url("?")
    False
    """
    if " " in txt or "\n" in txt:
        return False
    if "/" in txt:
        return True
    if re.search(r'\?\w+=.+', txt):
        return True
    if re.match(r"\w+\.html", txt):
        return True
    return False


def link_to_url(link):
    """
    >>> from scrapy.link import Link
    >>> link_to_url(Link("http://example.com/?foo=bar"))
    'http://example.com/?foo=bar'
    >>> link_to_url(Link("http://example.com/?foo=bar", fragment="id1"))
    'http://example.com/?foo=bar#id1'
    >>> link_to_url(Link("http://example.com/?foo=bar", fragment="!start"))
    'http://example.com/?foo=bar#!start'
    """
    if link.fragment and link.fragment != '#':
        return "#".join([link.url, link.fragment])
    return link.url


def url_fingerprint(url):
    url = canonicalize_url(url, keep_fragments=True)
    return hashlib.sha1(url.encode()).hexdigest()


def allowed_re(url, hard_url_constraint):
    r"""
    Construct a regexp to check for allowed urls. The url must be within
    the start domain or lower (unless hard_url_constraint is True), but can
    have or not have "www" subdomain and any of http/https protocols.

    >>> allowed_re('http://www.example.com/foo', True)
    re.compile('^https?://(www\\.)?example\\.com\\/foo', re.IGNORECASE)
    >>> allowed_re('http://www.example.com/foo', False)
    re.compile('^https?://([a-z0-9-.]+\\.)?example\\.com', re.IGNORECASE)
    >>> allowed_re('https://example.com/foo', False)
    re.compile('^https?://([a-z0-9-.]+\\.)?example\\.com', re.IGNORECASE)
    >>> allowed_re('https://blog.example.com/foo', True)
    re.compile('^https?://blog\\.example\\.com\\/foo', re.IGNORECASE)
    >>> allowed_re('https://blog.example.com/foo', False)
    re.compile('^https?://([a-z0-9-.]+\\.)?blog\\.example\\.com', re.IGNORECASE)
    >>> bool(allowed_re('https://example.com/foo', False).match('http://www.example.com/bar'))
    True
    >>> bool(allowed_re('https://example.com/foo', True).match('http://www.example.com/bar'))
    False
    >>> bool(allowed_re('https://example.com/foo', False).match('http://blog.example.com/bar'))
    True
    >>> bool(allowed_re('http://example.com/foo', False).match('http://blog.example.com/foo'))
    True
    >>> bool(allowed_re('http://blog.example.com', False).match('http://news.example.com'))
    False
    """
    if not hard_url_constraint:
        p = urlsplit(url)
        url = '{}://{}'.format(p.scheme, p.netloc)
    http = r'^https?://'
    http_www = http + r'(www\.)?'
    url = re.sub(http_www, '', url)
    if hard_url_constraint:
        p = urlsplit('http://' + url)
        if len(p.netloc.split('.')) > 2:
            regexp_prefix = http
        else:
            regexp_prefix = http_www
    else:
        regexp_prefix = http + r'([a-z0-9-.]+\.)?'
    return re.compile(regexp_prefix + re.escape(url), re.I)
