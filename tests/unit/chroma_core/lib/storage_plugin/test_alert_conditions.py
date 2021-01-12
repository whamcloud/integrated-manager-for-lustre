from tests.unit.lib.emf_unit_test_case import EMFUnitTestCase

from chroma_core.lib.storage_plugin.api import alert_conditions


class FakeResource:
    def __init__(self, status):
        self.status = status


class TestAlertConditions(EMFUnitTestCase):
    def test_attrvalalertcondition_empty(self):
        avac = alert_conditions.ValueCondition("status", id="avac")
        self.assertListEqual(avac.alert_classes(), [])
        result = avac.test(FakeResource("ERROR"))
        self.assertListEqual(result, [])

    def test_attrvalalertcondition(self):
        avac = alert_conditions.ValueCondition(
            "status",
            error_states=["ERROR"],
            warn_states=["WARN"],
            info_states=["INFO"],
            message="Alert raised now",
            id="avac",
        )

        import logging

        classes = avac.alert_classes()
        self.assertListEqual(
            classes,
            ["_avac_status_%s" % logging.ERROR, "_avac_status_%s" % logging.WARNING, "_avac_status_%s" % logging.INFO],
        )

        result = avac.test(FakeResource("OTHER"))
        self.assertListEqual(
            result,
            [
                ["_avac_status_%s" % logging.ERROR, "status", False, logging.ERROR],
                ["_avac_status_%s" % logging.WARNING, "status", False, logging.WARNING],
                ["_avac_status_%s" % logging.INFO, "status", False, logging.INFO],
            ],
        )
        result = avac.test(FakeResource("ERROR"))
        self.assertListEqual(
            result,
            [
                ["_avac_status_%s" % logging.ERROR, "status", True, logging.ERROR],
                ["_avac_status_%s" % logging.WARNING, "status", False, logging.WARNING],
                ["_avac_status_%s" % logging.INFO, "status", False, logging.INFO],
            ],
        )
        result = avac.test(FakeResource("WARN"))
        self.assertListEqual(
            result,
            [
                ["_avac_status_%s" % logging.ERROR, "status", False, logging.ERROR],
                ["_avac_status_%s" % logging.WARNING, "status", True, logging.WARNING],
                ["_avac_status_%s" % logging.INFO, "status", False, logging.INFO],
            ],
        )
        result = avac.test(FakeResource("INFO"))
        self.assertListEqual(
            result,
            [
                ["_avac_status_%s" % logging.ERROR, "status", False, logging.ERROR],
                ["_avac_status_%s" % logging.WARNING, "status", False, logging.WARNING],
                ["_avac_status_%s" % logging.INFO, "status", True, logging.INFO],
            ],
        )
