# -*- coding: utf-8 -*-
# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from chroma_core.lib.job import Step
from chroma_core.models import Job
from chroma_help.help import help_text
from django.contrib.postgres import fields

import json


class ConfigureLDevStep(Step):
    def run(self, kwargs):
        ldev_entries = kwargs["ldev_entries"]
        ldev_entries = json.loads(ldev_entries)

        for (fqdn, entries) in ldev_entries.items():
            self.invoke_rust_agent_expect_result(fqdn, "create_ldev_conf", entries)


class ConfigureLDevJob(Job):
    verb = "Configure LDev"
    ldev_entries = fields.JSONField(default={})

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls):
        return help_text["configure_ldev"]

    def description(self):
        return self.long_description()

    def get_steps(self):
        return [(ConfigureLDevStep, {"ldev_entries": self.ldev_entries})]
