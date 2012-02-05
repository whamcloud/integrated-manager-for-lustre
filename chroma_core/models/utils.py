
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models, transaction
from django.contrib.contenttypes.generic import GenericForeignKey

from polymorphic.models import DowncastManager
from polymorphic.models import PolymorphicMetaclass


class WorkaroundGenericForeignKey(GenericForeignKey):
    """TEMPORARY workaround for django bug #16048 while we wait for
       a fixed django to get released"""
    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        try:
            return getattr(instance, self.cache_attr)
        except AttributeError:
            rel_obj = None

            # Make sure to use ContentType.objects.get_for_id() to ensure that
            # lookups are cached (see ticket #5570). This takes more code than
            # the naive ``getattr(instance, self.ct_field)``, but has better
            # performance when dealing with GFKs in loops and such.
            f = self.model._meta.get_field(self.ct_field)
            ct_id = getattr(instance, f.get_attname(), None)
            if ct_id:
                ct = self.get_content_type(id=ct_id, using=instance._state.db)
                from django.core.exceptions import ObjectDoesNotExist
                try:
                    rel_obj = ct.model_class()._base_manager.using(ct._state.db).get(pk=getattr(instance, self.fk_field))

                except ObjectDoesNotExist:
                    pass
            setattr(instance, self.cache_attr, rel_obj)
            return rel_obj


class DeletableDowncastableManager(DowncastManager):
    """Filters results to return only not-deleted records"""
    def get_query_set(self):
        return super(DeletableDowncastableManager, self).get_query_set().filter(not_deleted = True)


class DeletableManager(models.Manager):
    """Filters results to return only not-deleted records"""
    def get_query_set(self):
        return super(DeletableManager, self).get_query_set().filter(not_deleted = True)


def _make_deletable(metaclass, dct):
    @classmethod
    # commit_on_success to ensure that the object is only marked deleted
    # if the updates to alerts also succeed
    @transaction.commit_on_success
    def delete(clss, id):
        """Mark a record as deleted, returns nothing.

        Looks up the model instance by pk, sets the not_deleted attribute
        to None and saves the model instance.

        Additionally marks any AlertStates referring to this item as inactive.

        This is provided as a class method which takes an ID rather than as an
        instance method, in order to use ._base_manager rather than .objects -- this
        allows us to find the object even if it was already deleted, making this
        operation idempotent rather than throwing a DoesNotExist on the second try.
        """
        # Not implemented as an instance method because
        # we will need to use _base_manager to ensure
        # we can get at the object
        instance = clss._base_manager.get(pk = id)
        if hasattr(instance, 'content_type'):
            klass = instance.content_type.model_class()
        else:
            klass = instance.__class__

        if instance.not_deleted:
            instance.not_deleted = None
            instance.save()

        from chroma_core.lib.lustre_audit import audit_log
        from chroma_core.models.alert import AlertState
        updated = AlertState.filter_by_item_id(klass, id).update(active = None)
        audit_log.info("Lowered %d alerts while deleting %s %s" % (updated, klass, id))

    dct['objects'] = DeletableManager()
    dct['delete'] = delete
    # Conditional to only create the 'deleted' attribute on the immediate
    # user of the metaclass, not again on subclasses.
    if issubclass(dct.get('__metaclass__', type), metaclass):
        # Please forgive me.  Logically this would be a field called 'deleted' which would
        # be True or False.  Instead, it is a field called 'not_deleted' which can be
        # True or None.  The reason is: unique_together constraints.
        dct['not_deleted'] = models.NullBooleanField(default = True)

    if 'Meta' in dct:
        if hasattr(dct['Meta'], 'unique_together'):
            if not 'not_deleted' in dct['Meta'].unique_together:
                dct['Meta'].unique_together = dct['Meta'].unique_together + ('not_deleted',)


class DeletableMetaclass(models.base.ModelBase):
    """Make a django model 'deletable', such that the default delete() method
    (an SQL DELETE) is replaced with something which keeps the record in the
    database but will hide it from future queries.

    The not_deleted attribute is logically a True/False 'deleted' attribute, but is
    implemented this (admittedly ugly) way in order to work with django's
    unique_together option.  When 'not_deleted' is included in the unique_together
    tuple, the uniqeness constraint is applied only to objects which have not
    been deleted -- e.g. an MGS can only have one filesystem with a given name, but
    once you've deleted that filesystem you should be able to create more with the
    same name.
    """
    def __new__(cls, name, bases, dct):
        _make_deletable(cls, dct)
        return super(DeletableMetaclass, cls).__new__(cls, name, bases, dct)


class DeletableDowncastableMetaclass(PolymorphicMetaclass):
    """Make a django model 'downcastable and 'deletable'.

    This combines the DowncastMetaclass behavior with the not_deleted attribute,
    the delete() method and the DeletableDowncastableManager.

    The not_deleted attribute is logically a True/False 'deleted' attribute, but is
    implemented this (admittedly ugly) way in order to work with django's
    unique_together option.  When 'not_deleted' is included in the unique_together
    tuple, the uniqeness constraint is applied only to objects which have not
    been deleted -- e.g. an MGS can only have one filesystem with a given name, but
    once you've deleted that filesystem you should be able to create more with the
    same name.

    The manager we set is a subclass of polymorphic.models.DowncastManager, so we inherit the
    full DowncastMetaclass behaviour.
    """
    def __new__(cls, name, bases, dct):
        _make_deletable(cls, dct)
        return super(DeletableDowncastableMetaclass, cls).__new__(cls, name, bases, dct)


class MeasuredEntity(object):
    """Provides mix-in access to metrics specific to the instance."""
    def __get_metrics(self):
        from chroma_core.lib.metrics import get_instance_metrics
        self._metrics = get_instance_metrics(self)
        return self._metrics

    metrics = property(__get_metrics)
