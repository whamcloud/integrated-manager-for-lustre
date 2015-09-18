#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import json

from collections import namedtuple
from django.db import models
from django.contrib.contenttypes.generic import GenericForeignKey

import chroma_core.models


class VariantGenericForeignKey(GenericForeignKey):
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
            ct_id = getattr(instance, self.ct_field, None)
            if ct_id:
                ct = self.get_content_type(id=ct_id, using=instance._state.db)
                try:
                    rel_obj = ct.get_object_for_this_type(pk=getattr(instance, self.fk_field))
                except models.ObjectDoesNotExist:
                    pass
            setattr(instance, self.cache_attr, rel_obj)
            return rel_obj

VariantDescriptor = namedtuple('VariantDescriptor', ['name', 'type', 'getter', 'setter', 'default'])


class SparseManager(models.Manager):
    """Filters results to return only not-deleted records"""
    def get_query_set(self):
        if getattr(self.model, 'is_sparse_base', False):
            return super(SparseManager, self).get_query_set()
        else:
            # This is a work in progress.
            # self.model.__class__.__name__ gives the SparseMetaclass which isn't want I expect or want.
            record_type = str(self.model).split('.')[-1:][0][:-2]
            return super(SparseManager, self).get_query_set().filter(record_type=record_type)


class SparseMetaclass(models.base.ModelBase):
    def __new__(cls, name, bases, dct):
        dct['objects'] = SparseManager()
        return super(SparseMetaclass, cls).__new__(cls, name, bases, dct)

    def __instancecheck__(self, instance):
        return self._instance_check(instance.__class__)

    def _instance_check(self, klass):
            if klass == SparseModel:
                return True

            for base in klass.__bases__:
                if self._instance_check(base):
                    return True

            return False


class SparseModel(models.Model):
    __metaclass__ = SparseMetaclass

    class Meta:
        abstract = True
        app_label = 'chroma_core'

    class UnknownSparseModel(KeyError):
        pass

    record_type = models.CharField(max_length = 128, default="")

    # Provide some space where an Alert can store some adhoc data of its own, also 5 adhoc strings.
    # This won't be searchable (except by class specific code but does allow some variation if required in subclasses.
    # It is supposed that this will be used to store a json representation of the data.
    # This should probably go into parent class.
    variant = models.CharField(max_length = 512, default = "{}")
    variant_fields = []
    variant_fields_inited = []

    @classmethod
    def __new__(cls, *args, **kwargs):
        try:
            if kwargs != {}:
                if 'record_type' not in kwargs:
                    kwargs['record_type'] = cls.__name__
                required_class = getattr(chroma_core.models, kwargs['record_type'])
            else:
                # The args will be in the order of the fields, but we add 1 because the cls is appended on the front.
                record_type_index = [field.attname for field in cls._meta.fields].index('record_type') + 1
                required_class = getattr(chroma_core.models, args[record_type_index])

            if (cls != required_class):
                args = (required_class,) + args[1:]
                instance = required_class.__new__(*args, **kwargs)

                # We have to call init because python won't because we are returning a different type.
                instance.__init__(*args[1:], **kwargs)
            else:
                instance = super(SparseModel, cls).__new__(cls)
                cls._init_variants()

            return instance
        except StopIteration:
            raise cls.UnknownSparseModel("SparseModel %s unknown" % cls)

    def __init__(self, *args, **kwargs):
        if kwargs and 'record_type' not in kwargs:
            kwargs['record_type'] = self.__class__.__name__

        super(SparseModel, self).__init__(*args, **kwargs)

    def get_variant(self, name, default, type_):
        try:
            assert isinstance(name, str)
            assert isinstance(type_, type)
            assert isinstance(default, type_)
        except:
            pass

        value = json.loads(self.variant).get(name, default)
        try:
            value = type_(value)
        except:
            pass
        return value

    def set_variant(self, name, type_, value):
        try:
            assert isinstance(name, str)
            assert isinstance(type_, type)
        except:
            pass
        try:
            value = type_(value)
        except:
            pass
        new_variant = json.loads(self.variant)
        new_variant[name] = value
        self.variant = json.dumps(new_variant)

    @classmethod
    def _init_variants(cls):
        def create_attr(variant):
            '''
            Create the property for the variant, simple call of special getter/setter or call of get/set variant. This
            setattr has to be in a function because each property needs its only instance of the variant variable and so
            if they just sit in the loop they share an instance and all have the attributes of the last entry in the
            variant_fields list.
            '''
            setattr(cls,
                    variant.name,
                    property(variant.getter if variant.getter else lambda self_: self_.get_variant(variant.name, variant.default, variant.type),
                             variant.setter if variant.setter else lambda self_, value: self_.set_variant(variant.name, variant.type, value)))

        # We only want to create the class attributes once, so keep track of classes already processed
        # and do not do them more than once.
        if cls not in cls.variant_fields_inited:
            for variant in cls.variant_fields:
                create_attr(variant)
            cls.variant_fields_inited.append(cls)

    def cast(self, target_class):
        """
        This allows a record to be cast into another type of record on that is based on the same table and has the same variant fields. In future we can
        work on making variant changes possible but for now it allows simple changes for things like command alerts.

        Typical usage:
        new_command_failed_alert = old_command_successful_alert(CommandFailedAlert)

        Not when you do this in the case above old_command_successful_alert is now invalid and should be discarded, the record type changes a new
        record is not created.

        :param target_class:
        :return: A new instance in the target class.
        """

        assert self.table_name == target_class.table_name, "Invalid cast %s to %s, tables names differ" % (self._meta.object_name, target_class._meta.object_name)
        assert sorted([variant.name for variant in self.variant_fields]) == sorted([variant.name for variant in target_class.variant_fields]), \
            "Invalid cast %s to %s, variant fields differ." % (self._meta.object_name, target_class._meta.object_name)

        # This should really come from target_class.__class__ but for some Python reason that gives the meta_class
        # not the class, which seems wrong to me but is the python way. I should ask I guess.
        self.record_type = target_class._meta.object_name
        self.save()
        return target_class.objects.get(id = self.id)
