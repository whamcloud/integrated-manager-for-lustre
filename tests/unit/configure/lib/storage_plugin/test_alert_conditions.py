
from django.test import TestCase

from configure.lib.storage_plugin import alert_conditions


class FakeResource:
    def __init__(self, status):
        self.status = status


class TestAlertConditions(TestCase):
    def test_attrvalalertcondition_empty(self):
        avac = alert_conditions.AttrValAlertCondition('status')
        avac.set_name('avac')
        self.assertListEqual(avac.alert_classes(), [])
        result = avac.test(FakeResource('ERROR'))
        self.assertListEqual(result, [])

    def test_attrvalalertcondition(self):
        avac = alert_conditions.AttrValAlertCondition('status', error_states = ["ERROR"], warn_states = ["WARN"], info_states = ["INFO"], message = "Alert raised now")

        # Fake up populating _name as manager would do when an alert condition
        # is a member of a resource
        avac.set_name('avac')

        import logging
        classes = avac.alert_classes()
        self.assertListEqual(classes, [
            '_avac_status_%s' % logging.ERROR,
            '_avac_status_%s' % logging.WARNING,
            '_avac_status_%s' % logging.INFO
            ])

        result = avac.test(FakeResource('OTHER'))
        self.assertListEqual(result, [
            ['_avac_status_%s' % logging.ERROR, 'status', False],
            ['_avac_status_%s' % logging.WARNING, 'status', False],
            ['_avac_status_%s' % logging.INFO, 'status', False]])
        result = avac.test(FakeResource('ERROR'))
        self.assertListEqual(result, [
            ['_avac_status_%s' % logging.ERROR, 'status', True],
            ['_avac_status_%s' % logging.WARNING, 'status', False],
            ['_avac_status_%s' % logging.INFO, 'status', False]])
        result = avac.test(FakeResource('WARN'))
        self.assertListEqual(result, [
            ['_avac_status_%s' % logging.ERROR, 'status', False],
            ['_avac_status_%s' % logging.WARNING, 'status', True],
            ['_avac_status_%s' % logging.INFO, 'status', False]])
        result = avac.test(FakeResource('INFO'))
        self.assertListEqual(result, [
            ['_avac_status_%s' % logging.ERROR, 'status', False],
            ['_avac_status_%s' % logging.WARNING, 'status', False],
            ['_avac_status_%s' % logging.INFO, 'status', True]])
