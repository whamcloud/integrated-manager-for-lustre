from iml_common.lib.evaluator import safe_eval
from iml_common.test.iml_unit_testcase import ImlUnitTestCase


class TestEvaluator(ImlUnitTestCase):
    def test_good_evaluation(self):
        var1 = 101242123
        var_2 = 12124.242442
        variable__three = "TestCase"
        integer_1 = 99
        integer_2 = 55
        bool_true = True
        bool_false = False

        properties = {
            "var1": var1,
            "var_2": var_2,
            "variable__three": variable__three,
            "integer_1": integer_1,
            "integer_2": integer_2,
            "bool_true": bool_true,
            "bool_false": bool_false,
        }

        expressions = [
            "1 * 2",
            "var1 == var_2",
            "var1 != var_2",
            "var1 - var_2",
            "(var1*var1)-var_2",
            "(var1 + var1) * (var_2 * var_2)",
            "(var1 + var1) / (var_2 * var_2)",
            "var1 + var1 * var_2 * var_2",
            "integer_1 % integer_2",
            "var1 < var_2",
            "var1 > var_2",
            "var1 <= var_2",
            "var1 >= var_2",
            "var1 <= var1",
            "var1 >= var1",
            "bool_true == True",
            "bool_true == True",
            "bool_true != True",
            "bool_false == False",
            "bool_true == bool_true",
            "bool_false == bool_true",
            "bool_false == bool_false",
            "bool_true == bool_false",
            "(bool_true == bool_false) or bool_true",
            "bool_true and bool_false",
            "bool_true and bool_true",
            "variable__three == variable__three",
            '(variable__three == "TestCase") and bool_true',
            "(variable__three == 'TestCase') and bool_true",
        ]

        for expression in expressions:
            self.assertEqual(eval(expression), safe_eval(expression, properties), expression)

    def test_bad_evaluation(self):
        var1 = 101242123
        variable__three = "TestCase"

        properties = {"var1": var1, "variable__three": variable__three}
        expression_exceptions = [
            ("1 / 0", ZeroDivisionError),
            ("rubbish", ValueError),
            ('eval("ls .")', TypeError),
            ("var1 / (var1 - var1)", ZeroDivisionError),
            ("var1 / (var1 - var1", SyntaxError),
            ("variable_three == 'TestCase'", ValueError),
        ]

        for expression_exception in expression_exceptions:
            with self.assertRaises(expression_exception[1]):
                safe_eval(expression_exception[0], properties)
