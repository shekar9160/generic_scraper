# -*- coding: utf-8 -*-
from __future__ import absolute_import

import tempfile
import uuid
from urllib.parse import urlsplit

from twisted.internet import defer
from twisted.web.resource import Resource
from twisted.web.util import Redirect

from .mockserver import MockServer
from .test_spider import html, SpiderTestCase, find_item


def get_session_id(request):
    return request.received_cookies.get(b'_uctest_auth')


def is_authenticated(request):
    session_id = get_session_id(request)
    if session_id not in SESSIONS:
        return False

    if SESSIONS[session_id]:
        return True
    else:
        request.setHeader(b'set-cookie', b'_uctest_auth=')
        return False


def authenticated_text(content):
    class R(Resource):
        def render_GET(self, request):
            if not is_authenticated(request):
                return Redirect(b'/login').render(request)
            else:
                return content.encode()
    return R


SESSIONS = {}  # session_id -> logged_in?


class Login(Resource):
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
                session_id = bytes(uuid.uuid4().hex, 'ascii')
                SESSIONS[session_id] = True
                request.setHeader(b'set-cookie', b'_uctest_auth=' + session_id)
            return Redirect(b'/').render(request)

    class _Index(Resource):
        isLeaf = True

        def render_GET(self, request):
            if is_authenticated(request):
                return html(
                    '<a href="/hidden">hidden</a> '
                    '<a href="/file.pdf">file.pdf</a>'
                ).encode()
            else:
                return html('<a href="/login">Login</a>').encode()

    def __init__(self):
        super().__init__()
        self.putChild(b'', self._Index())
        self.putChild(b'login', self._Login())
        self.putChild(b'hidden', authenticated_text(html('hidden resource'))())
        self.putChild(b'file.pdf', authenticated_text('data')())


class LoginIfUserAgentOk(Login):
    class _Login(Login._Login):
        def render_POST(self, request):
            user_agent = request.requestHeaders.getRawHeaders(b'User-Agent')
            if user_agent != [b'MyCustomAgent']:
                return html("Invalid User-Agent: %s" % user_agent).encode('utf8')
            return super(LoginIfUserAgentOk._Login, self).render_POST(request)


class LoginWithLogout(Login):
    class _Logout(Resource):
        isLeaf = True

        def render_GET(self, request):
            session_id = get_session_id(request)
            if session_id is not None:
                SESSIONS[session_id] = False
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
        self.tempdir = tempfile.TemporaryDirectory()
        return {
            'USERNAME': 'admin',
            'PASSWORD': 'secret',
            'LOGIN_URL': '/login',
            'FILES_STORE': 'file://' + self.tempdir.name,
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
        assert len(spider.collected_items) == 3
        assert {urlsplit(item['url']).path for item in spider.collected_items}\
            == {'/', '/hidden', '/file.pdf'}
        file_item = find_item('/file.pdf', spider.collected_items)
        with open(file_item['obj_stored_url'], 'rb') as f:
            assert f.read() == b'data'

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
            == {'/', '/hidden', '/one', '/two', '/three', '/file.pdf'}


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
