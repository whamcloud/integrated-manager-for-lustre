
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

def small_timesince(date):
    from datetime import datetime, timedelta
    delta = datetime.now() - date

    if delta < timedelta(seconds=60):
        result = "%s seconds" % delta.seconds
    elif delta < timedelta(minutes=60):
        result = "%s minutes" % (delta.seconds / 60)
    else:
        result = "%sh %sm" % (delta.seconds / 3600, delta.seconds / 60)

    return mark_safe("%s" % result)

register = template.Library()
register.filter('small_timesince', small_timesince)
