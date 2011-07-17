
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

import re
nid_regex = re.compile("(\d{1,3}\.){3}\d{1,3}@tcp(_\d+)?")
target_regex = re.compile("\\b(\\w+-(MDT|OST)\\d\\d\\d\\d)\\b")

from django import template
class StatusNode(template.Node):
    def __init__(self, item_name, var_name):
        self.item = template.Variable(item_name)
        self.var_name = var_name

    def render(self, context):
        all_statuses = template.Variable('all_statuses').resolve(context)
        status = all_statuses[self.item.resolve(context)]
        context[self.var_name] = status
        return ''

def do_status_lookup(parser, token):
    tag_name, item_name, as_keyword, var_name = token.split_contents()
    return StatusNode(item_name, var_name)

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
register.tag('status_lookup', do_status_lookup)


