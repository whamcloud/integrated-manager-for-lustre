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
        ("chroma_core", "0018_sfa_json_notify"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lustreclientmount",
            name="filesystem",
            field=models.CharField(help_text=b"Mounted filesystem", max_length=1024),
        ),
        migrations.RunPython(resolve_fk),
        migrations.RemoveField(model_name="managedhost", name="client_filesystems",),
    ]
