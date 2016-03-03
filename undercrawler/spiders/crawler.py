import re

import scrapy
from scrapy.linkextractors import LinkExtractor

from undercrawler.items import PageItem


class CrawlerSpider(scrapy.Spider):
    name = 'crawler'

    def __init__(self, url, *args, **kwargs):
        self.start_url = url
        self.link_extractor = LinkExtractor(
            allow=re.compile('^' + url, re.I))
        super().__init__(*args, **kwargs)

    def start_requests(self):
        yield self.splash_request(self.start_url)

    def parse(self, response):
        yield PageItem(url=response.url) #, body=response.body)
        for link in self.link_extractor.extract_links(response):
            yield self.splash_request(link.url)

    def splash_request(self, url):
        return scrapy.Request(
            url,
            # TODO - fix response.url in scrapyjs?
            callback=lambda response: self.parse(response.replace(url=url)),
            meta={
                'splash': {
                    'endpoint': 'render.html',
                    'html': 1,
                }
            },
        )
