# -*- coding: utf-8 -*-
# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import namedtuple
import re

from django.db import models
from django.db.models import CASCADE


class Nid(models.Model):
    """Simplified NID representation for those we detect already-configured"""

    lnet_configuration = models.ForeignKey("LNetConfiguration", on_delete=CASCADE)
    network_interface = models.OneToOneField("NetworkInterface", primary_key=True, on_delete=CASCADE)

    lnd_network = models.IntegerField(null=True, help_text="The lustre network number for this link")
    lnd_type = models.CharField(null=True, max_length=32, help_text="The protocol type being used over the link")

    @property
    def nid_string(self):
        return "%s@%s%s" % (self.network_interface.inet4_address, self.lnd_type, self.lnd_network)

    @property
    def modprobe_entry(self):
        return "%s%s(%s)" % (self.lnd_type, self.lnd_network, self.network_interface.name)

    @property
    def to_tuple(self):
        return tuple([self.network_interface.inet4_address, self.lnd_type, self.lnd_network])

    @classmethod
    def nid_tuple_to_string(cls, nid):
        return "%s@%s%s" % (nid.nid_address, nid.lnd_type, nid.lnd_network)

    Nid = namedtuple("Nid", ["nid_address", "lnd_type", "lnd_network"])

    @classmethod
    def lnd_types_for_network_type(cls, network_type):
        try:
            return {"tcp": ["tcp"], "o2ib": ["tcp", "o2ib"]}[network_type]
        except KeyError:
            raise KeyError("Unknown network type %s" % network_type)

    @classmethod
    def split_nid_string(cls, nid_string):
        """
        :param nid_string: Can be multiple format tcp0, tcp, tcp1234, o2ib0, o2ib (not number in the word)
        :return: Nid name tuple containing the address, the lnd_type or the lnd_network
        """
        assert "@" in nid_string, "Malformed NID?!: %s"

        # Split the nid so we can search correctly on its parts.
        nid_address = nid_string.split("@")[0]
        type_network_no = nid_string.split("@")[1]
        m = re.match("(\w+?)(\d+)?$", type_network_no)  # Non word, then optional greedy number at end of line.
        lnd_type = m.group(1)
        lnd_network = m.group(2)
        if not lnd_network:
            lnd_network = 0

        return Nid.Nid(nid_address, lnd_type, lnd_network)

    class Meta:
        app_label = "chroma_core"
        ordering = ["network_interface"]
