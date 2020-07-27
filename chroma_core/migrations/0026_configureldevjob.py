# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-08-17 18:02
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("chroma_core", "0025_createsnapshotjob_destroysnapshotjob"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfigureLDevJob",
            fields=[
                (
                    "job_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="chroma_core.Job",
                    ),
                ),
            ],
            options={"ordering": ["id"],},
            bases=("chroma_core.job",),
        ),
    ]