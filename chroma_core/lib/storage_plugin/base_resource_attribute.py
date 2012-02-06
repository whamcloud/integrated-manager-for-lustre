

class BaseResourceAttribute(object):
    """Base class for declared attributes of StorageResource.  This is
       to StorageResource as models.fields.Field is to models.Model"""

    # This is a hack to store the order in which attributes are declared so
    # that I can sort the StorageResource attribute dict for presentation in the same order
    # as the plugin author declared the attributes.
    creation_counter = 0

    def __init__(self, subscribe = None, provide = None, optional = False, label = None):
        self.optional = optional
        self.subscribe = subscribe
        self.provide = provide
        self.label = label

        self.creation_counter = BaseResourceAttribute.creation_counter
        BaseResourceAttribute.creation_counter += 1

    def get_label(self, name):
        if self.label:
            return self.label
        else:
            words = name.split("_")
            return " ".join([words[0].title()] + words[1:])

    def validate(self, value):
        """Note: this validation is NOT intended to be used for catching cases
        in production, it does not provide hooks for user-friendly error messages
        etc.  Think of it more as an assert."""
        pass

    def human_readable(self, value):
        """Subclasses should format their value for human consumption, e.g.
           1024 => 1kB"""
        return value

    def encode(self, value):
        import json
        return json.dumps(value)

    def decode(self, value):
        import json
        return json.loads(value)

    def to_markup(self, value):
        from django.utils.html import conditional_escape
        return conditional_escape(value)
