import scrapy


class PageItem(scrapy.Item):
    url = scrapy.Field()
    text = scrapy.Field()

    def __repr__(self):
        return repr({'url': self['url']})


class FormItem(scrapy.Item):
    url = scrapy.Field()
    form_type = scrapy.Field()
