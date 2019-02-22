# Copyright (c) 2019 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models


class Repo(models.Model):
    repo_name = models.CharField(primary_key=True, max_length=50, help_text="Unicode string, repo name")
    version = models.CharField(max_length=255, default="0.0.0", help_text="Unicode string, repo version")
    location = models.CharField(max_length=255, help_text="Unicode string, repo location")
    description = models.CharField(max_length=255, help_text="Unicode string, repo description")

    class Meta:
        unique_together = ("repo_name",)
        app_label = "chroma_core"
