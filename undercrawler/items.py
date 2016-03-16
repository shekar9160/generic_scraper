import scrapy


class PageItem(scrapy.Item):
    url = scrapy.Field()
    text = scrapy.Field()
    is_page = scrapy.Field()
    depth = scrapy.Field()

    def __repr__(self):
        return repr({
            'url': self['url'],
            'is_page': self['is_page'],
            'depth': self['depth'],
        })


class FormItem(scrapy.Item):
    url = scrapy.Field()
    form_type = scrapy.Field()
