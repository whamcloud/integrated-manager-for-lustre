#!/usr/bin/env python
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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
import glob

# To refresh all the boilerplates to this whilst at the tip of the source tree
# find . \( -name "*.py" -o -name "*.js" \) -exec scripts/boilerplate.py freshen {} \;


class BoilerPlate(object):
    def __init__(self, filename):
        self.boilerplate_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "boilerplates")

        self.filename = filename
        self.lines = open(filename, 'r').readlines()

        # Get the boilerplate
        self.boilerplate = self._load_boilerplate(os.path.join(self.boilerplate_path, "current.txt"))

        # Get the old boilerplates
        self.old_boilerplates = []

        for filename in glob.glob(os.path.join(self.boilerplate_path, "old_*")):
            self.old_boilerplates.append(self._load_boilerplate(filename))

    def save_file(self):
        open(self.filename, 'w').writelines(self.lines)

    def _load_boilerplate(self, filename):
        return [self.delimiter + line for line in open(filename, 'r').readlines()]

    @property
    def filetype(self):
        if filename.endswith(".py"):
            return("python")
        if filename.endswith(".js"):
            return("javascript")

        raise NotImplementedError("Unknown file type")

    @property
    def delimiter(self):
        try:
            return {"python": "#",
                    "javascript": "//"}[self.filetype]
        except KeyError:
            raise NotImplementedError("Unknown delimiter type")

    def apply_boilerplate(self, old_boilerplate):
        PRE_BOILERPLATE = '^(#(?:!|\s*vim:|\s*-\*-|\s*coding=utf-8).*|\s*)$'

        # See if we can find the old boiler plater intelligently
        if (old_boilerplate == None) or (self.find_boilerplate(old_boilerplate) == -1):
            # skip shebang lines etc
            insert_at = 0
            try:
                while re.search(PRE_BOILERPLATE, self.lines[insert_at]):
                    insert_at += 1
            except IndexError:
                # Nothing but a header
                return

            # Wipe other comments out (including old boilerplate)
            try:
                while self.lines[insert_at].startswith(self.delimiter) or self.lines[insert_at].strip() == "":
                    del self.lines[insert_at]
            except IndexError:
                # Overran file before finding non-whitespace, it's not code
                return
        else:
            insert_at = self.find_boilerplate(old_boilerplate)
            self.lines[insert_at:insert_at + len(old_boilerplate)] = []

        # Bit of a nicety here, we want a couple of blank lines after the boiler plate
        while (self.lines[insert_at] != "\n") or (self.lines[insert_at + 1] != "\n"):
            self.lines.insert(insert_at, "\n")

        self.lines = self.lines[0:insert_at] + self.boilerplate + self.lines[insert_at:]

        self.save_file()

    def find_boilerplate(self, boilerplate):
        for index, line in enumerate(self.lines):
            if boilerplate == self.lines[index:index + len(boilerplate)]:
                return index

        return -1

    def freshen_boilerplate(self):
        for old_boilerplate in self.old_boilerplates:
            if self.find_boilerplate(old_boilerplate) != -1:
                self.apply_boilerplate(old_boilerplate)
                self.save_file()
                break


try:
    command = sys.argv[1]
    filename = sys.argv[2]
except IndexError:
    print "Usage: boilerplate.py <test|apply|freshen> <filename>"
    sys.exit(-1)

boiler_plate = BoilerPlate(filename)

if command == 'apply':
    boiler_plate.apply_boilerplate(None)
elif command == 'freshen':
    boiler_plate.freshen_boilerplate()
elif command == 'test':
    if boiler_plate.lines and boiler_plate.find_boilerplate(boiler_plate.boilerplate) == -1:
        print "%s missing copyright boilerplate" % filename
        sys.exit(-2)
else:
    print "Unknown command %s" % command
    sys.exit(-1)
