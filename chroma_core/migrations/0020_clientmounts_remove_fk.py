# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def resolve_fk(apps, schema_editor):
    ClientMount = apps.get_model("chroma_core", "LustreClientMount")
    ManagedFilesystem = apps.get_model("chroma_core", "ManagedFilesystem")
    for m in ClientMount.objects.all():
        m.filesystem = ManagedFilesystem.objects.get(id=m.filesystem).name
        m.save()


class Migration(migrations.Migration):

    dependencies = [
        ("chroma_core", "0019_auto_20200529_2026"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lustreclientmount",
            name="filesystem",
            field=models.CharField(help_text=b"Mounted filesystem", max_length=8),
        ),
        migrations.RunPython(resolve_fk),
        migrations.RemoveField(model_name="managedhost", name="client_filesystems",),
    ]
