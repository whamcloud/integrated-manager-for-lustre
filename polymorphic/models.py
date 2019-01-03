from django.db import models
from django.db.models.base import ModelBase
from django.db.models.query import QuerySet
from django.contrib.contenttypes.models import ContentType


# http://djangosnippets.org/snippets/1343/
def nested_commit_on_success(func):
    """Like commit_on_success, but doesn't commit existing transactions.

    This decorator is used to run a function within the scope of a
    database transaction, committing the transaction on success and
    rolling it back if an exception occurs.

    Unlike the standard transaction.commit_on_success decorator, this
    version first checks whether a transaction is already active.  If so
    then it doesn't perform any commits or rollbacks, leaving that up to
    whoever is managing the active transaction.
    """
    from django.db import transaction

    commit_on_success = transaction.commit_on_success(func)

    def _nested_commit_on_success(*args, **kwds):
        if transaction.is_managed():
            return func(*args, **kwds)
        else:
            return commit_on_success(*args, **kwds)

    return transaction.wraps(func)(_nested_commit_on_success)


class PolymorphicMetaclass(ModelBase):
    def __new__(cls, name, bases, dct):
        def save(self, *args, **kwargs):
            if not self.content_type:
                self.content_type = ContentType.objects.get_for_model(self.__class__)

            # We make sure this is happening inside a transaction
            # because otherwise another thread could try to get
            # objects of the base class, this metaclass will try
            # to downcast, and fail because the instance of the
            # child DB object hasn't been saved yet.
            @nested_commit_on_success
            def base_save():
                models.Model.save(self, *args, **kwargs)

            base_save()

        @property
        def downcast_class(self):
            return ContentType.objects.get_for_id(self.content_type_id).model_class()

        def downcast(self):
            """Lookup the concrete subclass of a StatefulObject by leveraging Django caching

            If you have calling code that lands here, and really wants a fresh object,
            consider making a DB query to fetch the latest copy.  For example
                    model._base_manager.get(id=self.id)

            See chroma_core.services.job_scheduler.job_scheduler.JobScheduler#available_transitions for an example.

            """

            # TODO: reconsider usefulness of MTI: https://jira.hpdd.intel.com/browse/HYD-1367
            # TODO: review cache usage: https://jira.hpdd.intel.com/browse/HYD-3155

            model = self.downcast_class
            if model == self.__class__:
                return self

            # This returns the value of another attribute named
            #    "_%s_cache" % model.__name__.lower() on self
            # from cache; it hits db to fill cache if necessary
            # See also:  https://docs.djangoproject.com/en/dev/topics/db/models/#multi-table-inheritance
            # See also: django.db.models.fields.related.SingleRelatedObjectDescriptor#__get__
            # BEWARE of this cache going stale, which will happen, like any cache, when an object has
            # been sitting in it too long, such that it may have diverged in state from the DB.
            # And, certainly, do not call downcast, and expect the an object to be any fresher.  Look it up in the DB.
            return getattr(self, model.__name__.lower())

        if issubclass(dct.get("__metaclass__", type), PolymorphicMetaclass):
            dct["content_type"] = models.ForeignKey(ContentType, editable=False, null=True)
            dct["save"] = save
            dct["downcast"] = downcast
            dct["downcast_class"] = downcast_class

        return super(PolymorphicMetaclass, cls).__new__(cls, name, bases, dct)


class DowncastMetaclass(PolymorphicMetaclass):
    def __new__(cls, name, bases, dct):
        dct["objects"] = DowncastManager()
        return super(DowncastMetaclass, cls).__new__(cls, name, bases, dct)


class DowncastManager(models.Manager):
    def get_query_set(self):
        return DowncastQuerySet(self.model)


class DowncastQuerySet(QuerySet):
    def __getitem__(self, k):
        result = super(DowncastQuerySet, self).__getitem__(k)
        if isinstance(result, models.Model):
            return result.downcast()
        else:
            return result

    def __iter__(self):
        for item in super(DowncastQuerySet, self).__iter__():
            yield item.downcast()
