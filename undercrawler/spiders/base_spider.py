import formasaurus
import scrapy
from scrapy.linkextractors import LinkExtractor

from ..items import PageItem, FormItem


class BaseSpider(scrapy.Spider):
    name = 'base'

    def __init__(self, url, *args, **kwargs):
        if url.startswith('.'):
            with open(url) as f:
                self.start_urls = [line.strip() for line in f]
        else:
            self.start_urls = [url]
        self.link_extractor = LinkExtractor(allow=self.start_urls)
        super().__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.start_urls:
            yield self.splash_request(url)

    def splash_request(self, url, callback=None, **kwargs):
        callback = callback or self.parse
        return scrapy.Request(url, callback=callback, **kwargs)

    def parse(self, response):
        url = response.url
        self.logger.info(url)
        yield PageItem(url=url, body=response.body)
        if response.text:
            for _, meta in formasaurus.extract_forms(response.text):
                yield FormItem(url=url, form_type=meta['form'])
                self.logger.info('Found a %s form at %s', meta['form'], url)
        for link in self.link_extractor.extract_links(response):
            yield self.splash_request(link.url)
