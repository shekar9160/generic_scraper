import os.path


def cached_property(name):
    def deco(fn):
        def inner(self):
            cached = getattr(self, name)
            if cached is None:
                cached = fn(self)
                setattr(self, name, cached)
            return cached
        return property(inner)
    return deco


def extract_text(response):
    return '\n'.join(response.xpath('//body').xpath('string()').extract())


def load_directive(filename):
    root = os.path.join(os.path.dirname(__file__), 'directives')
    with open(os.path.join(root, filename)) as f:
        return f.read()


def using_splash(settings):
    return bool(settings.get('SPLASH_URL'))
