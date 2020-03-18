# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.db import migrations
from chroma_core.migrations import (
    to_default_table,
    forward_trigger_template,
    backward_trigger_template,
    join,
)

tables = map(to_default_table, ["chroma_core_device", "chroma_core_devicehost"])

forward_trigger_list = map(forward_trigger_template, tables)
forward_trigger_str = join(forward_trigger_list)

backward_trigger_list = map(backward_trigger_template, tables)
backward_trigger_str = join(backward_trigger_list)


class Migration(migrations.Migration):
    dependencies = [("chroma_core", "0026_merge_20200313_0745")]

    operations = [migrations.RunSQL(sql=forward_trigger_str, reverse_sql=backward_trigger_str)]
