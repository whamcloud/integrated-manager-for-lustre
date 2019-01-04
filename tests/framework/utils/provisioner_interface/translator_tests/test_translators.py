from django.utils.unittest import TestCase
import os
import tempfile
import shutil
import json

from chroma_core.lib.util import CommandLine


class TranslatorTests(TestCase, CommandLine):
    TESTCASE_DIR = os.path.abspath(os.path.dirname(__file__))
    RAW_JSON = os.path.join(TESTCASE_DIR, "raw_config.json")
    OUT_JSON = os.path.join(TESTCASE_DIR, "provisioner_input.json")
    IN_JSON = os.path.join(TESTCASE_DIR, "provisioner_output.json")
    FINAL_JSON = os.path.join(TESTCASE_DIR, "final_config.json")

    OUT_TRANSLATOR = os.path.join(TESTCASE_DIR, "..", "test_json2provisioner_json.py")
    IN_TRANSLATOR = os.path.join(TESTCASE_DIR, "..", "provisioner_json2test_json.py")

    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        os.environ["BUILD_JOB_NAME"] = "chroma-reviews"
        os.environ["BUILD_JOB_BUILD_NUMBER"] = "857"

        self.maxDiff = None
        self.addCleanup(lambda: shutil.rmtree(self.test_root))

    def test_raw_to_provisioner(self):
        test_output = os.path.join(self.test_root, "provisioner_input.json")
        self.try_shell(["python", self.OUT_TRANSLATOR, self.RAW_JSON, test_output])
        with open(self.OUT_JSON) as f:
            reference_data = json.load(f)

        with open(test_output) as f:
            test_data = json.load(f)

        self.assertEqual(test_data, reference_data)

    def test_provisioner_to_final(self):
        final_output = os.path.join(self.test_root, "final_config.json")
        self.try_shell(["python", self.IN_TRANSLATOR, self.IN_JSON, final_output])
        with open(self.FINAL_JSON) as f:
            reference_data = json.load(f)

        with open(final_output) as f:
            test_data = json.load(f)

        self.assertEqual(test_data, reference_data)
