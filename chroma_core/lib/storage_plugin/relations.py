

class BaseRelation(object):
    @property
    def key(self):
        return "%s_%s" % (self.subscribe_to, self.attributes)

    def val(self, resource):
        return tuple([getattr(resource, field_name) for field_name in self.attributes])


class Subscribe(BaseRelation):
    def __init__(self, subscribe_to, attributes):
        self.attributes = attributes
        self.subscribe_to = subscribe_to


class Provide(BaseRelation):
    def __init__(self, provide_to, attributes):
        self.attributes = attributes
        self.provide_to = provide_to
