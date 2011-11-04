
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

import re
nid_regex = re.compile("(\d{1,3}\.){3}\d{1,3}@tcp(_\d+)?")
target_regex = re.compile("\\b(\\w+-(MDT|OST)\\d\\d\\d\\d)\\b")

from configure.models import Nid, ManagedHost

# XXX tsk tsk tsk.  this is a copy of the same function from 
#     monitor/lib/lustre_audit.py
#     we need to build a library of this kind of stuff that everyone
#     can use
def normalize_nid(string):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow 
       direct comparisons between NIDs"""
    if string[-4:] == "@tcp":
        string += "0"

    # remove _ from nids (i.e. @tcp_0 -> @tcp0
    i = string.find("_")
    if i > -1:
        string = string[:i] + string [i + 1:]

    return string

def pretty_log_line(log_entry):
    message = log_entry.message
    service = log_entry.syslogtag
    date = log_entry.devicereportedtime.strftime("%b %d %H:%M:%S")
    host = log_entry.fromhost

    date = conditional_escape(date)
    host = conditional_escape(host)
    try:
        host_obj = ManagedHost.objects.get(address__startswith = host)
        host = "<a href='#'>%s</a>" % host
    except ManagedHost.DoesNotExist:
        pass
    service = conditional_escape(service)
    message = conditional_escape(message)

    for match in nid_regex.finditer(message):
        replace = match.group()
        replace = normalize_nid(replace)
        try:
            address =  Nid.objects.get(nid_string = replace).host.address
            markup = "<a href='#' title='%s'>%s</a>" % (match.group(), address)
            message = message.replace(match.group(),
                       markup,
                       1)
        except Nid.DoesNotExist:
            print "failed to replace " + replace

    for match in target_regex.finditer(message):
        # TODO: look up to a target and link to something useful
        replace = match.group()
        markup = "<a href='#' title='%s'>%s</a>" % ("foo", match.group())
        message = message.replace(match.group(),
                   markup,
                   1)

    return mark_safe("<span class='log_date'>%s</span> <span class='log_host'>%s</span> <span class='log_service'>%s</span>: <span class='log_message'>%s</span>" % (date, host, service, message))

def systemevent_css_class(systemevent):
    return mark_safe("log_line %s" % systemevent.get_message_class())

register = template.Library()
register.filter('pretty_log_line', pretty_log_line)
register.filter('systemevent_css_class', systemevent_css_class)
