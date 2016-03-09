import scrapy


class PageItem(scrapy.Item):
    url = scrapy.Field()
    body = scrapy.Field()


class FormItem(scrapy.Item):
    url = scrapy.Field()
    form_type = scrapy.Field()
