from django.test import TestCase


class IMLUnitTestCase(TestCase):
    # I added this class as a base because I needed a common action for all unit tests.
    # However that action it turned out was not needed, but by then all the work of changing
    # all the bases we done and so it makes sense I think to keep that work so the IML base
    # class still exists for future user.
    pass
