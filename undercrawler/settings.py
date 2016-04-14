BOT_NAME = 'undercrawler'

SPIDER_MODULES = ['undercrawler.spiders']
NEWSPIDER_MODULE = 'undercrawler.spiders'

ROBOTSTXT_OBEY = False
DEPTH_LIMIT = 20

USE_SPLASH = True
SPLASH_URL = 'http://127.0.0.1:8050'

AUTOLOGIN_URL = 'http://127.0.0.1:8089'
AUTOLOGIN_ENABLED = True
CRAZY_SEARCH_ENABLED = True

CDR_CRAWLER = 'scrapy undercrawler'
CDR_TEAM = 'HG'

PREFER_PAGINATION = True
ADBLOCK = False
MAX_DOMAIN_SEARCH_FORMS = 10
HARD_URL_CONSTRAINT = False
AVOID_DUP_CONTENT_ENABLED = True

FILES_STORE_S3_ACL = 'public-read'
# Set FILES_STORE to enable
ITEM_PIPELINES = {'undercrawler.documents_pipeline.CDRDocumentsPipeline': 1}

DOWNLOADER_MIDDLEWARES = {
    'undercrawler.middleware.AvoidDupContentMiddleware': 200,
    'undercrawler.middleware.AutologinMiddleware': 584,
    'undercrawler.middleware.SplashAwareAutoThrottle': 722,
}
if USE_SPLASH:
    DOWNLOADER_MIDDLEWARES.update({
        'scrapy_splash.SplashCookiesMiddleware': 723,
        'undercrawler.middleware.SplashMiddleware': 725,
        'scrapy.downloadermiddlewares.httpcompression'
            '.HttpCompressionMiddleware': 810,
    })
    DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'

# use the same user agent as autologin by default
USER_AGENT = ('Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Ubuntu Chromium/43.0.2357.130 '
              'Chrome/43.0.2357.130 Safari/537.36')

COOKIES_ENABLED = False

# Run full headless-horseman scripts
RUN_HH = True

DOWNLOAD_DELAY = 0.1  # Adjusted by AutoThrottle
SPLASH_AUTOTHROTTLE_ENABLED = True

# HH scripts in Splash take a while to execute, so use higher values here
CONCURRENT_REQUESTS = 32
CONCURRENT_REQUESTS_PER_DOMAIN = 32

DEPTH_PRIORITY = 1
SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'

RETRY_ENABLED = True


# Unused settings from template

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
