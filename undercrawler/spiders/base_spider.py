import re

import formasaurus
import scrapy
from scrapy.linkextractors import LinkExtractor

from ..items import PageItem, FormItem


class BaseSpider(scrapy.Spider):
    name = 'base'

    def __init__(self, url, *args, **kwargs):
        if url.startswith('.'):
            with open(url) as f:
                start_urls = [line.strip() for line in f]
        else:
            start_urls = [url]
        self.start_urls = [self._normalize_url(_url) for _url in start_urls]
        self.link_extractor = LinkExtractor(
            allow=[self._start_url_re(_url) for _url in self.start_urls])
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
        yield PageItem(url=url, text=response.text)
        if response.text:
            for _, meta in formasaurus.extract_forms(response.text):
                yield FormItem(url=url, form_type=meta['form'])
                self.logger.info('Found a %s form at %s', meta['form'], url)
        for link in self.link_extractor.extract_links(response):
            yield self.splash_request(link.url)

    def _normalize_url(self, url):
        if not url.startswith('http'):
            url = 'http://' + url
        return url

    def _start_url_re(self, url):
        http_www = r'^https?://(www\.)?'
        return re.compile(http_www + re.sub(http_www, '', url), re.I)
