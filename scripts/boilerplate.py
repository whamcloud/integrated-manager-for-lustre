#!/usr/bin/env python
#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


import sys
import re
import os

OLD_BOILERPLATES = {
    '.js': ['//\n// =+\n// Copyright \(c\) \d{4} Whamcloud, Inc\.\s*(?:All rights reserved\.)?\n// =+\n+'],
    '.py': ['(?:#\s*\n)*# =+\n# Copyright(?: \(c\))? \d{4} Whamcloud, Inc\.\s*(?:All rights reserved\.)?\n# =+\n+',
           '# Copyright \d{4} Whamcloud\n']}

PRE_BOILERPLATE = '^(#(?:!|\s*vim:|\s*-\*-|\s*coding=utf-8).*|\s*)$'

BOILERPLATE = {'.js': """//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


""", '.py': """#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


"""}


def apply_boilerplate(filename):
    if filename.endswith(".py"):
        lines = open(filename, 'r').readlines()
        if not lines:
            return

        # skip shebang lines etc
        insert_at = 0
        try:
            while re.search(PRE_BOILERPLATE, lines[insert_at]):
                insert_at += 1
        except IndexError:
            # Nothing but a header
            return

        # wipe other comments out (including old boilerplate)
        cursor = insert_at
        try:
            while lines[cursor][0] == '#' or lines[cursor].strip() == "":
                cursor += 1
        except IndexError:
            # Overran file before finding non-whitespace, it's not code
            return
        lines = lines[0:insert_at] + lines[cursor:]

        output = "".join(lines[0:insert_at]) + BOILERPLATE['.py'] + "".join(lines[insert_at:])
        open(filename, 'w').write(output)
    elif filename.endswith(".js"):
        if not has_boilerplate(filename):
            text = open(filename, 'r').read()
            # remove old boilerplate
            for old_boilerplate in OLD_BOILERPLATES['.js']:
                text = re.sub('^' + old_boilerplate, '', text)
            open(filename, 'w').write(BOILERPLATE['.js'] + text)
    else:
        raise NotImplementedError("Unknown extension %s" % filename)


def has_boilerplate(filename):
    if filename.endswith(".py"):
        text = open(filename, 'r').read()
        if not text.strip():
            return True

        try:
            text.index(BOILERPLATE['.py'])
            return True
        except ValueError:
            lines = [l for l in open(filename, 'r').readlines() if not (l.startswith("#") or l.strip() == "")]
            if lines:
                return False
            else:
                return True
    elif filename.endswith(".js"):
        text = open(filename, 'r').read()
        if text.startswith(BOILERPLATE['.js']):
            return True
        else:
            return False
    else:
        raise NotImplementedError("Unknown extension %s" % filename)


def freshen_boilerplate(filename):
    extension = os.path.splitext(filename)[1]

    if len(extension) and extension in OLD_BOILERPLATES:
        text = open(filename, 'r').read()
        for old_boilerplate in OLD_BOILERPLATES[extension]:
            if re.search(old_boilerplate, text):
                apply_boilerplate(filename)
                break
    else:
        raise NotImplementedError("Unknown extension %s" % filename)

try:
    command = sys.argv[1]
    filename = sys.argv[2]
except IndexError:
    print "Usage: boilerplate.py <test|apply> <filename>"
    sys.exit(-1)
if command == 'apply':
    apply_boilerplate(filename)
elif command == 'freshen':
    freshen_boilerplate(filename)
elif command == 'test':
    has = has_boilerplate(filename)
    if not has:
        print "Missing copyright boilerplate"
        sys.exit(-2)
else:
    print "Unknown command %s" % command
    sys.exit(-1)
