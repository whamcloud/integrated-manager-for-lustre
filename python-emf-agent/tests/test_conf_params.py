from chroma_agent.action_plugins.manage_conf_params import set_conf_param
from emf_common.test.command_capture_testcase import CommandCaptureTestCase


class TestConfParams(CommandCaptureTestCase):
    def test_conf_param_not_none(self):
        self.add_command(("lctl", "conf_param", "Rupert=1234"))

        set_conf_param(key="Rupert", value=1234)
        self.assertRanAllCommandsInOrder()

    def test_conf_param_not_none_but_zero(self):
        self.add_command(("lctl", "conf_param", "Stanley=0"))

        set_conf_param(key="Stanley", value=0)
        self.assertRanAllCommandsInOrder()

    def test_conf_param_none(self):
        self.add_command(("lctl", "conf_param", "-d", "Edgar"))

        set_conf_param(key="Edgar", value=None)
        self.assertRanAllCommandsInOrder()

    def test_conf_param_none_default(self):
        self.add_command(("lctl", "conf_param", "-d", "Edward"))

        set_conf_param(key="Edward")
        self.assertRanAllCommandsInOrder()
