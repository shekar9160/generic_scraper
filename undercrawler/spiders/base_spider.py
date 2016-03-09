import formasaurus
import scrapy
from scrapy.linkextractors import LinkExtractor

from ..items import PageItem, FormItem


class BaseSpider(scrapy.Spider):
    name = 'base'

    def __init__(self, url, *args, **kwargs):
        self.start_url = url
        self.link_extractor = LinkExtractor(allow=[url])
        super().__init__(*args, **kwargs)

    def start_requests(self):
        yield self.splash_request(self.start_url)

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
