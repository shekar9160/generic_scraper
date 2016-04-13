import os, uuid, tempfile
from urllib.parse import urlsplit

from twisted.internet import defer
from twisted.trial.unittest import TestCase
from twisted.web.resource import Resource
from twisted.web.util import Redirect
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from scrapy.utils.log import configure_logging

import undercrawler.settings
from undercrawler.spiders import BaseSpider
from tests.mockserver import MockServer


configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})


class SpiderTestCase(TestCase):
    settings = {}

    def setUp(self):
        settings = Settings()
        settings.setmodule(undercrawler.settings)
        settings['DOWNLOAD_DELAY'] = 0.1
        settings['ITEM_PIPELINES']['tests.utils.CollectorPipeline'] = 100
        splash_url = os.environ.get('SPLASH_URL')
        if splash_url:
            settings['SPLASH_URL'] = splash_url
        settings.update(self.settings)
        runner = CrawlerRunner(settings)
        self.crawler = runner.create_crawler(BaseSpider)


def html(content):
    return '<html><head></head><body>{}</body></html>'.format(content)


def text_resource(content):
    class Page(Resource):
        isLeaf = True
        def render_GET(self, request):
            return content.encode()
    return Page


SinglePage = text_resource(html('<b>hello</b>'))
SinglePage.__name__ = 'SinglePage'


class Follow(Resource):
    def __init__(self):
        super().__init__()
        self.putChild(b'', text_resource(
            html('<a href="/one">one</a> | <a href="/two">two</a>'))())
        self.putChild(b'one', text_resource('one')())
        self.putChild(b'two', text_resource('two')())


class TestBasic(SpiderTestCase):
    settings = {
        'AUTOLOGIN_ENABLED': False,
    }

    @defer.inlineCallbacks
    def test_single(self):
        with MockServer(SinglePage) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url)
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 1
        item = spider.collected_items[0]
        assert item['url'] == root_url + '/'
        assert item['extracted_text'] == 'hello'
        assert item['raw_content'] == html('<b>hello</b>')

    @defer.inlineCallbacks
    def test_follow(self):
        with MockServer(Follow) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url)
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 3
        spider.collected_items.sort(key=lambda item: item['url'])
        item0 = spider.collected_items[0]
        assert item0['url'] == root_url + '/'
        item1 = spider.collected_items[1]
        assert item1['url'] == root_url + '/one'
        assert item1['raw_content'] == html('one')
        item2 = spider.collected_items[2]
        assert item2['url'] == root_url + '/two'
        assert item2['raw_content'] == html('two')


class PDFFile(Resource):
    isLeaf = True
    def render_GET(self, response):
        response.setHeader(b'content-type', b'application/pdf')
        return b'pdf file content'


class WithFile(Resource):
    def __init__(self):
        super().__init__()
        self.putChild(b'', text_resource(
            html('<a href="/file.pdf">file</a>'))())
        self.putChild(b'file.pdf', PDFFile())


class TestDocuments(SpiderTestCase):
    @property
    def settings(self):
        self.tempdir = tempfile.TemporaryDirectory()
        return  {
            'AUTOLOGIN_ENABLED': False,
            'FILES_STORE': 'file://' + self.tempdir.name,
        }

    @defer.inlineCallbacks
    def test(self):
        with MockServer(WithFile) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url)
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 2
        file_item = spider.collected_items[1]
        assert file_item['url'] == file_item['obj_original_url'] == \
            root_url + '/file.pdf'
        with open(file_item['obj_stored_url']) as f:
            assert f.read() == 'pdf file content'
        assert file_item['content_type'] == 'application/pdf'


def is_authenticated(request):
    session_id = request.received_cookies.get(b'_uctest_auth')
    if not session_id:
        return False
    is_auth = session_id == Login.session_id
    if not is_auth and session_id:
        request.setHeader(b'set-cookie', b'_uctest_auth=')
    return is_auth


def authenticated_text(content):
    class R(Resource):
        def render_GET(self, request):
            if not is_authenticated(request):
                return Redirect(b'/login').render(request)
            else:
                return content.encode()
    return R


class Login(Resource):
    session_id = None

    class _Login(Resource):
        isLeaf = True
        def render_GET(self, request):
            return html(
                '<form action="/login" method="POSt">'
                '<input type="text" name="login">'
                '<input type="password" name="password">'
                '<input type="submit" value="Login">'
                '</form>').encode()
        def render_POST(self, request):
            if request.args[b'login'][0] == b'admin' and \
                    request.args[b'password'][0] == b'secret':
                Login.session_id = bytes(uuid.uuid4().hex, 'ascii')
                request.setHeader(
                    b'set-cookie', b'_uctest_auth=' + Login.session_id)
            return Redirect(b'/').render(request)

    class _Index(Resource):
        isLeaf = True
        def render_GET(self, request):
            if is_authenticated(request):
                return html('<a href="/hidden">Go get it</a>').encode()
            else:
                return html('<a href="/login">Login</a>').encode()

    def __init__(self):
        super().__init__()
        self.putChild(b'', self._Index())
        self.putChild(b'login', self._Login())
        self.putChild(b'hidden', authenticated_text(html('hidden resource'))())


class LoginWithLogout(Login):
    class _Logout(Resource):
        isLeaf = True
        def render_GET(self, request):
            Login.session_id = None
            request.setHeader(b'set-cookie', b'_uctest_auth=')
            return html('you have been logged out').encode()

    def __init__(self):
        super().__init__()
        self.putChild(b'hidden', authenticated_text(html(
            '<a href="/one">one</a> | '
            '<a href="/logout1">logout1</a> | '
            '<a href="/two">two</a> | '
            '<a href="/logout2">logout2</a> | '
            '<a href="/three">three</a>'
            ))())
        self.putChild(b'one', authenticated_text(html('1'))())
        self.putChild(b'logout1', self._Logout())
        self.putChild(b'two', authenticated_text(html('2'))())
        self.putChild(b'logout2', self._Logout())
        self.putChild(b'three', authenticated_text(html('3'))())


class TestAutologin(SpiderTestCase):
    @property
    def settings(self):
        return  {
            'USERNAME': 'admin',
            'PASSWORD': 'secret',
            'LOGIN_URL': '/login',
        }

    @defer.inlineCallbacks
    def test_login(self):
        ''' No logout links, just one page after login.
        '''
        with MockServer(Login) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url)
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 2
        assert spider.collected_items[1]['url'] == root_url + '/hidden'

    @defer.inlineCallbacks
    def test_login_with_logout(self):
        ''' Login with logout.
        '''
        with MockServer(LoginWithLogout) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url)
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert {urlsplit(item['url']).path for item in spider.collected_items}\
            == {'/', '/hidden', '/one', '/two', '/three'}


class LoginIfUserAgentOk(Login):
    class _Login(Login._Login):
        def render_POST(self, request):
            user_agent = request.requestHeaders.getRawHeaders(b'User-Agent')
            if user_agent != [b'MyCustomAgent']:
                Login.session_id = None
                return html("Invalid User-Agent: %s" % user_agent).encode('utf8')
            return super(LoginIfUserAgentOk._Login, self).render_POST(request)


class TestAutoLoginCustomHeaders(SpiderTestCase):
    @property
    def settings(self):
        return {
            'USERNAME': 'admin',
            'PASSWORD': 'secret',
            'LOGIN_URL': '/login',
            'USER_AGENT': 'MyCustomAgent',
        }

    @defer.inlineCallbacks
    def test_login(self):
        with MockServer(LoginIfUserAgentOk) as s:
            root_url = s.root_url
            yield self.crawler.crawl(url=root_url)
        spider = self.crawler.spider
        assert hasattr(spider, 'collected_items')
        assert len(spider.collected_items) == 2
        assert spider.collected_items[1]['url'] == root_url + '/hidden'
