from scrapy import Request
from scrapy_splash import SplashRequest

from undercrawler.dupe_filter import DupeFilter


def test_dupe_filter_with_splash():
    dupe_filter = DupeFilter()
    url_fp = lambda url: dupe_filter.request_fingerprint(SplashRequest(url))
    assert url_fp('http://example.com') == \
           url_fp('https://example.com')
    assert url_fp('http://www.example.com/foo?a=1&b=1') == \
           url_fp('http://example.com/foo?b=1&a=1')
    assert url_fp('http://example.com/foo') != \
           url_fp('http://example.com/bar')
    assert url_fp('http://www.example.com/foo?a=1&b=1') == \
           url_fp('http://example.com/foo?b=1&a=1')
    assert url_fp('http://www.example.com/foo#a') != \
           url_fp('http://example.com/foo#b')


def test_dupe_filter_without_splash():
    dupe_filter = DupeFilter()
    url_fp = lambda url: dupe_filter.request_fingerprint(Request(url))
    assert url_fp('http://example.com') != \
           url_fp('https://example.com')
    assert url_fp('http://www.example.com/foo?a=1&b=1') == \
           url_fp('http://www.example.com/foo?b=1&a=1')
    assert url_fp('http://example.com/foo') != \
           url_fp('http://example.com/bar')
    assert url_fp('http://www.example.com/foo?a=1&b=1') != \
           url_fp('http://example.com/foo?b=1&a=1')
    # splash is not used, so by default these urls are considered the same
    assert url_fp('http://www.example.com/foo#a') == \
           url_fp('http://www.example.com/foo#b')
