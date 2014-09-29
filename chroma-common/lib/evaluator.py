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


def safe_eval(s, subsitutions):
    for key, value in subsitutions.items():
        if (type(value) == str):
            value = "'%s'" % value

        s = s.replace(key, str(value))

    for key, value in {"False": "0", "True": "1"}.items():
        s = s.replace(key, value)

    node = ast.parse(s, mode='eval')

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
