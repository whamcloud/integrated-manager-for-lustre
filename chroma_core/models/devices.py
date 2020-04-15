from django.db import models
from django.contrib.postgres import fields

class Device(models.Model):
    fqdn = models.CharField(max_length=255, unique=True)
    device = fields.JSONField()
