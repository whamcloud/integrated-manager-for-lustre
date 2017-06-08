# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
        elif isinstance(node, ast.Name):
            # handle instances of ast.Name, this indicates unrecognised variables in expression
            raise ValueError('Unrecognised variable "{0}"'.format(node.id))
        else:
            raise TypeError('Unsupported type "{0}"'.format(node.__class__))

    return _eval(node.body)
