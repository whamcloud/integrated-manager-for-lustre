# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-11-24 15:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chroma_core", "0030_purge_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="cluster_id",
            field=models.IntegerField(help_text=b"The cluster this ticket belongs to", null=True),
        ),
        migrations.AlterField(
            model_name="runstratagemjob",
            name="action",
            field=models.TextField(default=b""),
        ),
        migrations.AlterField(
            model_name="runstratagemjob",
            name="search_expression",
            field=models.TextField(default=b"", null=True),
        ),
    ]