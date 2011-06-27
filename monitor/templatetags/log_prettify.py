
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

import re
nid_regex = re.compile("(\d{1,3}\.){3}\d{1,3}@tcp(_\d+)?")

from monitor.models import Nid, Host

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

def pretty_log_line(line):
    first_part = line.split(": ")[0]
    message = ": ".join(line.split(": ")[1:])
    date_len = len("Jun 16 15:38:54")
    date = first_part[0:date_len]
    host_and_service = first_part[date_len:]
    try:
        host,service = host_and_service.split()
    except ValueError:
        return line

    date = conditional_escape(date)
    host = conditional_escape(host)
    try:
        host_obj = Host.objects.get(address__startswith = host)
        host = "<a href='#'>%s</a>" % host
    except Host.DoesNotExist:
        pass
    service = conditional_escape(service)
    message = conditional_escape(message)

    i = nid_regex.finditer(message)
    for match in i:
        replace = match.group()
        replace = normalize_nid(replace)
        try:
            address =  Nid.objects.get(nid_string = replace).host.address
            markup = "<a href='#' title='%s'>%s</a>" % (address, match.group())
            message = message.replace(match.group(),
                       markup,
                       1)
        except Nid.DoesNotExist:
            print "failed to replace " + replace

    return mark_safe("<span class='log_date'>%s</span> <span class='log_host'>%s</span> <span class='log_service'>%s</span>: <span class='log_message'>%s</span>" % (date, host, service, message))

register = template.Library()
register.filter('pretty_log_line', pretty_log_line)
