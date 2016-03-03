import json
import os.path

import scrapy
from scrapy.linkextractors import LinkExtractor

from undercrawler.items import PageItem


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
        yield PageItem(url=response.url) #, body=response.body)
        for link in self.link_extractor.extract_links(response):
            yield self.splash_request(link.url)

    def splash_request(self, url):
        if self.crawler.settings.getbool('USE_HH'):
            callback = lambda r: self.handle_hh_response(url, r)
            splash = {
                'endpoint': 'execute',
                'args': {
                    'lua_source': self.lua_source,
                    'js_source': self.js_source,
                }}
        else:
            callback = lambda r: self.parse(r.replace(url=url))
            splash = {'endpoint': 'render.html'}
        return scrapy.Request(
            url, callback=callback, meta={'splash': splash})

    def handle_hh_response(self, url, response):
        data = json.loads(response.text)
        html_response = response.replace(
            url=url, body=data['html'].encode('utf-8'))
        return self.parse(html_response)
