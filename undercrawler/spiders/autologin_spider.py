from collections import defaultdict
from functools import partial
from http.cookies import SimpleCookie
from urllib.parse import urlparse

import formasaurus
from scrapy.exceptions import DontCloseSpider
from scrapy import signals

from ..items import PageItem
from .. import autologin, login_keychain
from .base_spider import BaseSpider


class AutologinSpider(BaseSpider):
    name = 'autologin'

    def __init__(self, *args, **kwargs):
        self.domain_states = defaultdict(DomainState)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.check_credentials, signals.spider_idle)
        return spider

    def parse(self, response):
        self.logger.info(response.url)
        domain_state = self.get_domain_state(response.url)
        if self.is_logout(domain_state, response):
            self.logger.info('Logged out at %s', response.url)
            domain_state.logged_in = False
            domain_state.logout_urls.add(response.url)
            login_url = domain_state.login_url
            if login_url is not None:
                self.logger.info('Will relogin at %s', login_url)
                # TODO - reset all pending requests
                yield self.splash_request(login_url, dont_filter=True)
        yield PageItem(url=response.url, text=response.text)
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
            self.logger.info('Found a login form at %s', url)
            yield from self.try_login(url, form)
        elif form_type == 'registration':
            self.logger.info('Found a registration form at %s', url)
            login_keychain.add_registration_task(
                url, max_per_domain=10)

    def handle_login_response(self, response, login_url):
        domain_state = self.get_domain_state(response.url)
        if self.is_successfull_login(domain_state, response):
            self.logger.info('Login successfull at %s', login_url)
            domain_state.logged_in = True
            domain_state.login_url = login_url
        else:
            self.logger.info('Login failed at %s', login_url)
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
                for url in list(domain_state.login_urls):
                    if login_keychain.get_credentials(url):
                        self.crawler.engine.crawl(
                            self.splash_request(url, dont_filter=True),
                            spider)
        if need_login and login_keychain.any_unsolved():
            self.logger.info('Waiting for credentials...')
            raise DontCloseSpider

    def try_login(self, url, form):
        domain_state = self.get_domain_state(url)
        domain_state.login_urls.add(url)
        if domain_state.logged_in:
            return
        credentials_list = login_keychain.get_credentials(url)
        if credentials_list:
            # TODO - try multiple credentials in case of failure via
            # a custom callback
            credentials = credentials_list[0]
            element, meta = form
            params = autologin.login_params(url, credentials, element, meta)
            if params:
                yield self.splash_request(
                    callback=partial(
                        self.handle_login_response, login_url=url),
                    **params)

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
        self.login_url = None
        self.login_urls = set()
        self.logout_urls = set()
        self.auth_cookies = set()
