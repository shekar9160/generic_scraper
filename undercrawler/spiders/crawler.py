import scrapy
from scrapy.exceptions import DontCloseSpider
from scrapy.linkextractors import LinkExtractor
from scrapy import signals
import formasaurus

from ..items import PageItem
from .. import autologin, login_keychain


class CrawlerSpider(scrapy.Spider):
    name = 'crawler'

    def __init__(self, url, *args, **kwargs):
        self.start_url = url
        self.link_extractor = LinkExtractor(allow=[url])
        self.unused_login_forms = dict()  # url: form
        super().__init__(*args, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.check_login_forms, signals.spider_idle)
        return spider

    def start_requests(self):
        yield self.splash_request(self.start_url)

    def splash_request(self, url, **kwargs):
        return scrapy.Request(url, callback=self.parse, **kwargs)

    def parse(self, response):
        yield PageItem(url=response.url, body=response.body)
        if response.text:
            for form in formasaurus.extract_forms(response.text):
                yield from self.handle_form(response.url, form)
        for link in self.link_extractor.extract_links(response):
            yield self.splash_request(link.url)

    def handle_form(self, url, form):
        _, meta = form
        form_type = meta['form']
        if form_type == 'login':
            yield from self.try_login(url, form)
        elif form_type == 'registration':
            login_keychain.add_registration_task(url)

    def check_login_forms(self, spider):
        if spider != self or not self.unused_login_forms:
            return
        self.logger.debug('checking login forms')
        for url, form in list(self.unused_login_forms.items()):
            for request in self.try_login(url, form):
                self.crawler.engine.crawl(request, spider)
        if login_keychain.any_unsolved():
            raise DontCloseSpider

    def try_login(self, url, form):
        credentials_list = login_keychain.get_credentials(url)
        if credentials_list:
            self.unused_login_forms.pop(url, None)
            # TODO - try multiple credentials in case of failure via
            # a custom callback
            credentials = credentials_list[0]
            element, meta = form
            params = autologin.login_params(url, credentials, element, meta)
            if params:
                # TODO - recrawl everything after successfull login
                yield self.splash_request(**params)
        else:
            self.unused_login_forms[url] = form
