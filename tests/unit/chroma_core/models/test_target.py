from chroma_core.models import GenerateHaLabelStep
from chroma_core.models.jobs import Job
from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase

# Illegal chars for NCName
ILLEGAL_CHARS = set(":@$%&/+,;()[]{} \r\n\t")
ILLEGAL_LEADING_CHARS = set("0123456789.-")


class TestHaLabel(IMLUnitTestCase):
    def setUp(self):
        super(TestHaLabel, self).setUp()

        self.fake_halabel_step = GenerateHaLabelStep(Job(), None, None, None, None)

    def check_label(self, label_text):
        """Check that the fully sanitized label is legal"""

        matching_illegal_chars = ILLEGAL_CHARS.intersection(set(label_text))
        self.assertTrue(len(matching_illegal_chars) == 0, "%s found in %s" % (matching_illegal_chars, label_text))
        self.assertTrue(label_text[0] not in ILLEGAL_LEADING_CHARS, label_text[0])

    def test_sanitize_ha_label(self):
        """Test that for possible filesystems result is ok ha_label names"""

        self.check_label(self.fake_halabel_step.sanitize_name("key:@$%&/+,;illegals"))
        self.check_label(self.fake_halabel_step.sanitize_name("allparens[]{}()"))
        self.check_label(self.fake_halabel_step.sanitize_name("the \t\r\nspaces"))
        self.check_label(self.fake_halabel_step.sanitize_name("1leadingnumber"))
        self.check_label(self.fake_halabel_step.sanitize_name(".ledwithdot"))
        self.check_label(self.fake_halabel_step.sanitize_name("-ledwithdash"))
        self.check_label(self.fake_halabel_step.sanitize_name("--ledwit2hdashes"))
        self.check_label(self.fake_halabel_step.sanitize_name("foo_bar"))
        self.check_label(self.fake_halabel_step.sanitize_name("_foo_bar_"))
        self.check_label(self.fake_halabel_step.sanitize_name("rep$$$$$$$$$eat.....ed"))
        self.check_label(self.fake_halabel_step.sanitize_name("A123456789"))
        self.check_label(self.fake_halabel_step.sanitize_name("123456789"))

    def test_no_sanitize_ha_label(self):
        """Test that known good names aren not altered"""

        self.assertEqual(self.fake_halabel_step.sanitize_name("test-fs")[:-7], "test-fs")
        self.assertEqual(self.fake_halabel_step.sanitize_name("fs1")[:-7], "fs1")
        self.assertEqual(self.fake_halabel_step.sanitize_name("fs2")[:-7], "fs2")
        self.assertEqual(self.fake_halabel_step.sanitize_name("_scratchfs")[:-7], "_scratchfs")
        self.assertEqual(self.fake_halabel_step.sanitize_name("_scratchfs")[:-7], "_scratchfs")
        self.assertEqual(self.fake_halabel_step.sanitize_name("x2_fs")[:-7], "x2_fs")

    def test_expected_sanitizations_ha_label(self):
        self.assertEqual(self.fake_halabel_step.sanitize_name("12_fs")[:-7], "_2_fs")
