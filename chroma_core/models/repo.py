# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models


class Repo(models.Model):
    repo_name = models.CharField(primary_key=True, max_length=50, help_text="Unicode string, repo name")
    location = models.CharField(max_length=255, help_text="Unicode string, repo file location")

    @property
    def contents(self):
        return open(self.location).read()

    class Meta:
        unique_together = ("repo_name",)
        app_label = "chroma_core"
