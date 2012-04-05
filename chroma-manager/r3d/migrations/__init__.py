## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>

# Needed for custom field definitions
# http://south.aeracode.org/wiki/MyFieldsDontWork
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^r3d\.models\.SciFloatField"])
