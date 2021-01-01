from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ChromaCoreAppConfig(AppConfig):
    name = "chroma_core"
    verbose_name = "Chroma Core"

    def ready(self):
        from chroma_core.management import setup_groups

        post_migrate.connect(setup_groups, sender=self)
