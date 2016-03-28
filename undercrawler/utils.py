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
