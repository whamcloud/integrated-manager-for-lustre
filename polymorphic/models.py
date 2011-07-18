from django.db import models
from django.db.models.base import ModelBase
from django.db.models.query import QuerySet

class PolymorphicMetaclass(ModelBase):
    def __new__(cls, name, bases, dct):
        def downcast(self):
            for subklass in self.__class__.__subclasses__():
                attr = subklass.__name__.lower()
                try:
                    return getattr(self, attr)
                except subklass.DoesNotExist:
                    pass

            return self

        if issubclass(dct.get('__metaclass__', type), PolymorphicMetaclass):
          dct['downcast'] = downcast

        return super(PolymorphicMetaclass, cls).__new__(cls, name, bases, dct)

class DowncastMetaclass(PolymorphicMetaclass):
    def __new__(cls, name, bases, dct):
        dct['objects'] = DowncastManager()
        return super(DowncastMetaclass, cls).__new__(cls, name, bases, dct)

class DowncastManager(models.Manager):
    def get_query_set(self):
        return DowncastQuerySet(self.model)

class DowncastQuerySet(QuerySet):
    def __getitem__(self, k):
        result = super(DowncastQuerySet, self).__getitem__(k)
        if isinstance(result, models.Model) :
            return result.downcast()
        else :
            return result
    def __iter__(self):
        for item in super(DowncastQuerySet, self).__iter__():
            yield item.downcast()



