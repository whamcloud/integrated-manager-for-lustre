# -*- coding: utf-8 -*-
# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import json
import logging

from django.db import models
from django.db.models import CASCADE
from django.core.exceptions import ObjectDoesNotExist

from chroma_core.models import AlertStateBase
from chroma_core.models import AlertEvent
from chroma_core.models import DeletableStatefulObject
from chroma_core.models import StateChangeJob
from chroma_core.models import NullStateChangeJob
from chroma_core.models import Nid
from chroma_core.models import ManagedHost
from chroma_core.models import Job, AdvertisedJob, StateLock
from chroma_core.models import NetworkInterface
from chroma_core.lib.job import DependOn, DependAll, Step
from chroma_core.lib.util import invoke_rust_agent
from chroma_help.help import help_text
from django.db import connection


class ConfigureLDevStep(Step):
    def run(self, kwargs):
        #fqdn = self.invoke_rust_local_action_expect_result("get_mgs_host_fqdn")
        ldev_entries = self.invoke_rust_local_action_expect_result("create_ldev_conf")
        self.invoke_rust_agent(fqdn, "create_ldev_conf", ldev_entries)


class ConfigureLDevJob(Job):
    verb = "Configure LDev"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls):
        return help_text["configure_ldev"]

    def description(self):
        return self.long_description()

    def get_steps(self):
        return [(ConfigureLDevStep, {})]
