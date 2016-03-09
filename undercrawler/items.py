import scrapy


class PageItem(scrapy.Item):
    url = scrapy.Field()
    text = scrapy.Field()


class FormItem(scrapy.Item):
    url = scrapy.Field()
    form_type = scrapy.Field()
