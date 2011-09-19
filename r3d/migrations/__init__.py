# Needed for custom field definitions
# http://south.aeracode.org/wiki/MyFieldsDontWork
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^r3d\.models\.SciFloatField"])
