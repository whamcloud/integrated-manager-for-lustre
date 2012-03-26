
import random
from django.db import models

ID_LENGTH = 4  # in bytes


class AgentSession(models.Model):
    class Meta:
        app_label = 'chroma_core'

    host = models.ForeignKey('ManagedHost')
    session_id = models.CharField(max_length = ID_LENGTH * 2, default = lambda: "%.2x" * ID_LENGTH % tuple([random.SystemRandom().getrandbits(8) for i in range(0, ID_LENGTH)]))
    counter = models.IntegerField(default = 0)
