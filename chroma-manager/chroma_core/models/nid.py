# -*- coding: utf-8 -*-
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


from collections import namedtuple
import re

from django.db import models

import settings


class Nid(models.Model):
    """Simplified NID representation for those we detect already-configured"""
    lnet_configuration = models.ForeignKey('LNetConfiguration')
    network_interface = models.OneToOneField('NetworkInterface', primary_key = True)

    lnd_network = models.IntegerField(null=True,
                                      help_text = "The lustre network number for this link")
    lnd_type = models.CharField(null=True,
                                max_length=32,
                                help_text = "The protocol type being used over the link")

    @property
    def nid_string(self):
        return ("%s@%s%s" % (self.network_interface.inet4_address,
                             self.lnd_type,
                             self.lnd_network))

    @property
    def modprobe_entry(self):
        return("%s%s(%s)" % (self.lnd_type,
                             self.lnd_network,
                             self.network_interface.name))

    @property
    def to_tuple(self):
        return tuple([self.network_interface.inet4_address,
                      self.lnd_type,
                      self.lnd_network])

    @classmethod
    def nid_tuple_to_string(cls, nid):
        return ("%s@%s%s" % (nid.nid_address,
                             nid.lnd_type,
                             nid.lnd_network))

    Nid = namedtuple("Nid", ["nid_address", "lnd_type", "lnd_network"])

    @classmethod
    def lnd_types_for_network_type(cls, network_type):
        try:
            return settings.NETWORK_TYPE_TO_LND_TYPE[network_type]
        except KeyError:
            raise KeyError("Unknown network type %s" % network_type)

    @classmethod
    def split_nid_string(cls, nid_string):
        '''
        :param nid_string: Can be multiple format tcp0, tcp, tcp1234, o2ib0, o2ib (not number in the word)
        :return: Nid name tuple containing the address, the lnd_type or the lnd_network
        '''
        assert '@' in nid_string, "Malformed NID?!: %s"

        # Split the nid so we can search correctly on its parts.
        nid_address = nid_string.split("@")[0]
        type_network_no = nid_string.split("@")[1]
        m = re.match('(\w+?)(\d+)?$', type_network_no)   # Non word, then optional greedy number at end of line.
        lnd_type = m.group(1)
        lnd_network = m.group(2)
        if not lnd_network:
            lnd_network = 0

        return Nid.Nid(nid_address, lnd_type, lnd_network)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['network_interface']
