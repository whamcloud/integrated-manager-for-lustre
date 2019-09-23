from django.apps import AppConfig
from django.db.models.signals import post_migrate


def cb(sender, **kwargs):
    from chroma_core.models.power_control import create_default_power_types

    create_default_power_types(sender)


class ChromaCoreAppConfig(AppConfig):
    name = "chroma_core"
    verbose_name = "Chroma Core"

    def ready(self):
        from chroma_core.management import setup_groups

        post_migrate.connect(setup_groups, sender=self)
        post_migrate.connect(cb, sender=self)
