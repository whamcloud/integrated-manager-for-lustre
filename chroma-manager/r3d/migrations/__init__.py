#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^r3d\.models\.SciFloatField"])
add_introspection_rules([], ["^r3d\.models\.PickledObjectField"])
