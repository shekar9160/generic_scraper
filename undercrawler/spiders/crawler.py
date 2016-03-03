import json
import os.path

import scrapy
from scrapy.linkextractors import LinkExtractor
import formasaurus

from undercrawler.items import PageItem
from undercrawler import autologin, login_keychain


class CrawlerSpider(scrapy.Spider):
    name = 'crawler'

    def __init__(self, url, *args, **kwargs):
        self.start_url = url
        self.link_extractor = LinkExtractor(allow=[url])

        root = os.path.join(os.path.dirname(__file__), '../directives/')
        with open(os.path.join(root, 'headless_horseman.lua')) as f:
            self.lua_source = f.read()
        with open(os.path.join(root, 'headless_horseman.js')) as f:
            self.js_source = f.read()

        super().__init__(*args, **kwargs)

    def start_requests(self):
        yield self.splash_request(self.start_url)

    def parse(self, response):
        yield PageItem(url=response.url, body=response.body)
        if response.text:
            for form in formasaurus.extract_forms(response.text):
                yield from self.handle_form(response.url, form)
        for link in self.link_extractor.extract_links(response):
            yield self.splash_request(link.url)

    def splash_request(self, url):
        run_hh = self.crawler.settings.getbool('USE_HH')
        return scrapy.Request(
            url,
            callback=self.handle_hh_response,
            meta={
                'splash': {
                    'endpoint': 'execute',
                    'args': {
                        'lua_source': self.lua_source,
                        'js_source': self.js_source,
                        'run_hh': run_hh,
                    }
                }
            })

    def handle_hh_response(self, response):
        data = json.loads(response.text)
        html_response = response.replace(body=data['html'].encode('utf-8'))
        return self.parse(html_response)

    def handle_form(self, url, form):
        element, meta = form
        if meta['form'] == 'login':
            credentials = login_keychain.get_credentials(url)
            if credentials is not None:
                params = autologin.login_params(
                    url, credentials, element, meta)
                if params:
                    # TODO - cookies
                    yield scrapy.Request(callback=self.parse, **params)
