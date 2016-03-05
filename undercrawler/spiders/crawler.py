from urllib.parse import urlparse
from collections import defaultdict
from http.cookies import SimpleCookie

import scrapy
from scrapy.exceptions import DontCloseSpider
from scrapy.linkextractors import LinkExtractor
from scrapy import signals
import formasaurus
from scrapyjs import SplashAwareDupeFilter

from ..items import PageItem
from .. import autologin, login_keychain


class CrawlerSpider(scrapy.Spider):
    name = 'crawler'

    def __init__(self, url, *args, **kwargs):
        self.start_url = url
        self.link_extractor = LinkExtractor(allow=[url])
        self.domain_states = defaultdict(DomainState)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.check_credentials, signals.spider_idle)
        return spider

    def start_requests(self):
        yield self.splash_request(self.start_url)

    def splash_request(self, url, callback=None, **kwargs):
        callback = callback or self.parse
        return scrapy.Request(url, callback=callback, **kwargs)

    def parse(self, response):
        domain_state = self.get_domain_state(response.url)
        if self.is_logout(domain_state, response):
            self.logger.info('Logged out at %s', response.url)
            domain_state.logged_in = False
            domain_state.logout_urls.add(response.url)
            # TODO - reset all pending requests and go to login?
        self.logger.info(response.url)
        yield PageItem(url=response.url, body=response.body)
        if response.text:
            for form in formasaurus.extract_forms(response.text):
                yield from self.handle_form(response.url, form)
        for link in self.link_extractor.extract_links(response):
            if link.url not in domain_state.logout_urls:
                yield self.splash_request(link.url)

    def handle_form(self, url, form):
        _, meta = form
        form_type = meta['form']
        if form_type == 'login':
            yield from self.try_login(url, form)
        elif form_type == 'registration':
            self.logger.info('Found a registration form at %s', url)
            login_keychain.add_registration_task(url)

    def handle_login_response(self, response):
        domain_state = self.get_domain_state(response.url)
        if self.is_successfull_login(domain_state, response):
            self.logger.info('Login successfull at %s', response.url)
            domain_state.logged_in = True
        else:
            pass  # TODO?
        yield from self.parse(response)

    def is_successfull_login(self, domain_state, response):
        if response.status != 200:
            return False
        # FIXME - We rely on using splash here. Could we use CookiesMiddleware?
        cookies = (response.request.meta['splash']['args']['headers']
                   .get('cookie', ''))
        cookies = [x.split('=')[0] for x in cookies.split(';')]
        response_cookies = get_response_cookies(response)
        auth_cookies = set(response_cookies.keys()).difference(cookies)
        if auth_cookies:
            domain_state.auth_cookies = auth_cookies
            return True

    def is_logout(self, domain_state, response):
        return domain_state.logged_in and any(
            name in domain_state.auth_cookies and m.value == ''
            for name, m in get_response_cookies(response).items())

    def check_credentials(self, spider):
        if spider != self:
            return
        need_login = False
        for domain_state in self.domain_states.values():
            if not domain_state.logged_in:
                need_login = True
                for url, form in list(domain_state.login_forms.items()):
                    for request in self.try_login(url, form):
                        self.crawler.engine.crawl(request, spider)
        if need_login and login_keychain.any_unsolved():
            self.logger.info('Waiting for credentials...')
            raise DontCloseSpider

    def try_login(self, url, form):
        domain_state = self.get_domain_state(url)
        if domain_state.logged_in:
            return
        self.logger.info('Found a login form at %s', url)
        credentials_list = login_keychain.get_credentials(url)
        if credentials_list:
            domain_state.login_forms.pop(url, None)
            # TODO - try multiple credentials in case of failure via
            # a custom callback
            credentials = credentials_list[0]
            element, meta = form
            params = autologin.login_params(url, credentials, element, meta)
            if params:
                yield self.splash_request(
                    callback=self.handle_login_response, **params)
        else:
            domain_state.login_forms[url] = form

    def get_domain_state(self, url):
        return self.domain_states[urlparse(url).netloc]


def get_response_cookies(response):
    cookies = SimpleCookie()
    for set_cookie in response.headers.getlist('set-cookie'):
        cookies.load(set_cookie.decode('utf-8'))
    return cookies


class DomainState:
    def __init__(self):
        self.logged_in = False
        self.login_form = None
        self.login_forms = dict()  # url: form
        self.logout_urls = set()
        self.auth_cookies = set()
