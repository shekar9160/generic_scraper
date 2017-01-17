from setuptools import setup


setup(
    name='undercrawler',
    packages=['undercrawler'],
    install_requires=[
        'scrapy>=1.1.0',
        'botocore',
        'scrapy-splash>=0.6',
        'autologin-middleware',
        'MaybeDont',
        'Formasaurus[with_deps]>=0.8',
        'autopager>=0.2',
    ],
)
