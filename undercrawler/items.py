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


class CDRItem(scrapy.Item):

    # (url)-(crawl timestamp), SHA-256 hashed, UPPERCASE (string)
    _id = scrapy.Field()

    # MIME type (multi (strings))
    content_type = scrapy.Field()

    # Text label identifying the software used by the crawler (string)
    crawler = scrapy.Field()

    # Tika/other extraction output (object)
    extracted_metadata = scrapy.Field()

    # Tika/other extraction output (string)
    extracted_text = scrapy.Field()

    # Original source text/html (string)
    raw_content = scrapy.Field()

    # Text label identifying the team responsible for the crawler (string)
    team = scrapy.Field()

    # Timestamp of COLLECTION of data from the web (datetime)
    # https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping-date-format.html#built-in-date-formats
    timestamp = scrapy.Field()

    # Full URL requested by the crawler (multi (strings))
    url = scrapy.Field()

    # Schema version. This document describes schema version 2.0. (float)
    version = scrapy.Field()

    def __repr__(self):
        fields = ['_id', 'url', 'timestamp']
        return repr({f: self[f] for f in fields})
