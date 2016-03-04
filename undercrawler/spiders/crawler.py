import scrapy
from scrapy.linkextractors import LinkExtractor
import formasaurus

from ..items import PageItem
from .. import autologin, login_keychain


class CrawlerSpider(scrapy.Spider):
    name = 'crawler'

    def __init__(self, url, *args, **kwargs):
        self.start_url = url
        self.link_extractor = LinkExtractor(allow=[url])
        super().__init__(*args, **kwargs)

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
        element, meta = form
        form_type = meta['form']
        if form_type == 'login':
            credentials = login_keychain.get_credentials(url)
            if credentials is not None:
                params = autologin.login_params(
                    url, credentials, element, meta)
                if params:
                    yield self.splash_request(**params)
        elif form_type == 'registration':
            login_keychain.add_registration_task(url)
