#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import ast
import operator

binOps = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.div,
    ast.Mod: operator.mod,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: operator.and_,
    ast.Or: operator.or_
}


def safe_eval(expression, properties):
    '''
    safe_eval is an safe expression evaluator. It is fairly well featured and allows for all the operators
    defined abot in binops to be used, it can handle bracketing and understand operator precedence.

    The code takes an expression and a list of properties that will be substituted into the expression.

    For example the expression may be "zfs_installed == False" and the properties might be {"zfs_installed": True}

    Before evaluation this "zfs_installed == False" would be transformed to "1 == 0" - Note that as well as transforming
    the variables True/False and transformed to 1/0.

    The evaluator can return true/false (1/0) or arithmetic answers, it can also deal with string comparisons.

    :param expression: The expression to evaluate.
    :param properties: The properties to be used for the evaluation
    :return: The result of the evaluation or an exception.
    '''

    def substitute_properties(expression, properties):
        for prop, value in properties.items():
            # If the property is a string then it's value needs to be enclosed in quotes.
            if (type(value) == str):
                value = "'%s'" % value

            expression = expression.replace(prop, str(value))

        return expression

    expression = substitute_properties(expression, properties)                  # Sub our properties for their values
    expression = substitute_properties(expression, {'False': 0, 'True': 1})     # Turn False/True into 0/1

    node = ast.parse(expression, mode='eval')

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            return binOps[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.BoolOp):
            return binOps[type(node.op)](_eval(node.values[0]), _eval(node.values[1]))
        elif isinstance(node, ast.Compare):
            def _compare(ops, comparators):
                if len(ops) == 1:
                    return binOps[type(ops[0])](_eval(comparators[0]), _eval(comparators[1]))
                return binOps[type(ops[0])](_eval(comparators[0]), _compare(ops[1:], comparators[1:]))
            return _compare(node.ops, [node.left] + node.comparators)
        else:
            raise Exception('Unsupported type {}'.format(node))

    return _eval(node.body)
