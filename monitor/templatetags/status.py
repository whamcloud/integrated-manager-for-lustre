
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django import template

def status_class(status_string):
    return {
        "STARTED": "OK",
        "FAILOVER": "WARNING",
        "HA WARN": "WARNING",
        "RECOVERY": "WARNING",
        "REDUNDANT": "OK",
        "SPARE": "OK",
        "STOPPED": "OFFLINE",
        "???": "",
        "OFFLINE": "OFFLINE",
        "OK": "OK",
        "WARNING": "WARNING"
        }[status_string]

register = template.Library()
register.filter('status_class', status_class)


