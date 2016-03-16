BOT_NAME = 'undercrawler'

SPIDER_MODULES = ['undercrawler.spiders']
NEWSPIDER_MODULE = 'undercrawler.spiders'

ROBOTSTXT_OBEY = False
DEPTH_LIMIT = 20

USE_SPLASH = True
SPLASH_URL = 'http://127.0.0.1:8050'

AUTOLOGIN_URL = 'http://127.0.0.1:8089'
AUTOLOGIN_ENABLED = True

CDR_EXPORT = True
CDR_CRAWLER = 'scrapy undercrawler'
CDR_TEAM = 'HG'

PREFER_PAGINATION = True

DOWNLOADER_MIDDLEWARES = {
    'undercrawler.middleware.AutologinMiddleware': 584,
}
if USE_SPLASH:
    DOWNLOADER_MIDDLEWARES['undercrawler.middleware.HHSplashMiddleware'] = 585
    DUPEFILTER_CLASS = 'undercrawler.middleware.HHSplashAwareDupefilter'

COOKIES_ENABLED = False

# Run full headless-horseman scripts
RUN_HH = True

DOWNLOAD_DELAY = 3

CONCURRENT_REQUESTS = 32
# Using small value here to retry less requests due to logouts
CONCURRENT_REQUESTS_PER_DOMAIN = 4

DEPTH_PRIORITY = 1
SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'

RETRY_ENABLED = True

#AUTOTHROTTLE_ENABLED = True
#AUTOTHROTTLE_START_DELAY = 3
#AUTOTHROTTLE_MAX_DELAY = 60
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
#AUTOTHROTTLE_DEBUG = True


# Unused settings from template

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'undercrawler (+http://www.yourdomain.com)'

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'undercrawler.middlewares.MyCustomSpiderMiddleware': 543,
#}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    'undercrawler.pipelines.SomePipeline': 300,
#}

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
