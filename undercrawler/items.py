import scrapy


class PageItem(scrapy.Item):
    url = scrapy.Field()
    body = scrapy.Field()
