#!/usr/bin/env python

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


import os
import sys
import errno
import json
import requests

REGISTRY_BASE_URI = 'http://registry.npmjs.org/'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class SemanticVersion(object):
    def __init__(self, version_string):
        #print "vs: %s" % version_string
        if '-' in version_string:
            version_string = version_string[0:version_string.rindex('-')]
        if version_string == 'latest' or version_string == '*':
            version_string = 'x.x.x'
        if version_string.count('.') == 1:
            version_string += '.x'
        try:
            self.major, self.minor, self.patch = version_string.split('.')
        except ValueError:
            fatal("Malformed version string: %s" % version_string)
        if '~' in self.major:
            self.major = self.major.replace('~', '')
            self.patch = 'x'

        self.fuzzy_constraint = None
        if '<=' in self.major:
            self.major = self.major.replace('<=', '')
            self.fuzzy_constraint = '<='
            self.constraint_version = SemanticVersion(str(self))
        if '<' in self.major:
            self.major = self.major.replace('<', '')
            self.fuzzy_constraint = '<'
            self.constraint_version = SemanticVersion(str(self))
        if '>=' in self.major:
            self.major = self.major.replace('>=', '')
            self.fuzzy_constraint = '>='
            self.constraint_version = SemanticVersion(str(self))
        if '>' in self.major:
            self.major = self.major.replace('>', '')
            self.fuzzy_constraint = '>'
            self.constraint_version = SemanticVersion(str(self))
        if '=' in self.major:
            self.major = self.major.replace('=', '')

    def __str__(self):
        return "%s.%s.%s" % (self.major, self.minor, self.patch)

    def _cmp_attr(self, other, attr):
        if getattr(self, attr) == 'x':
            return 0
        else:
            return cmp(int(getattr(self, attr)), int(getattr(other, attr)))

    def __cmp__(self, other):
        if not other:
            return 1

        if self.fuzzy_constraint:
            if other >= self.constraint_version:
                if '=' in self.fuzzy_constraint and other == self.constraint_version:
                    return 0
                else:
                    return 1
            elif other <= self.constraint_version:
                if '=' in self.fuzzy_constraint and other == self.constraint_version:
                    return 0
                else:
                    return -1

        major = self._cmp_attr(other, 'major') * 100
        minor = self._cmp_attr(other, 'minor') * 10
        patch = self._cmp_attr(other, 'patch')

        return major + minor + patch

    def satisfied_by(self, other):
        if self.fuzzy_constraint:
            if '<=' == self.fuzzy_constraint:
                return other <= self.constraint_version
            elif '<' == self.fuzzy_constraint:
                return other < self.constraint_version
            elif '>=' == self.fuzzy_constraint:
                return other >= self.constraint_version
            elif '>' == self.fuzzy_constraint:
                return other > self.constraint_version
        else:
            return self == other and self <= other

    @property
    def is_fuzzy(self):
        return self.fuzzy_constraint or any([getattr(self, attr) == 'x' for attr in ['major', 'minor', 'patch']])


def fatal(msg=None):
    if msg:
        sys.stderr.write("FATAL: %s\n" % msg)

    sys.exit(1)


def warning(msg):
    sys.stderr.write("WARNING: %s\n" % msg)


def get_registry_metadata(name, version=None):
    uri = REGISTRY_BASE_URI + '%s/' % name
    if version:
        uri += '%s/' % version
    return requests.get(uri).json()


def resolve_fuzzy_version(name, fuzzy):
    best = None
    meta = get_registry_metadata(name)
    print "Resolving %s for %s" % (fuzzy, name)
    for version in [SemanticVersion(m_v) for m_v in meta['versions'].keys()]:
        if fuzzy.satisfied_by(version) and version > best:
            best = version

    if not best:
        fatal("Unable to resolve %s into x.y.z version" % fuzzy)

    print "Found %s for %s" % (best, name)
    return best


def build_dependency_tree(meta):
    deps = {}
    #print meta.get('dependencies', {})
    for name, version in [(n, SemanticVersion(v)) for n, v in meta.get('dependencies', {}).items()]:
        print "Checking %s-%s" % (name, version)
        if version.is_fuzzy:
            version = resolve_fuzzy_version(name, version)

        meta = get_registry_metadata(name, version)
        deps[name] = dict(version = version, meta = meta)
        for dep_name, dep_dict in build_dependency_tree(meta).items():
            if dep_name in deps and deps[dep_name]['version'] != dep_dict['version']:
                fatal("Incompatible dep version found for %s: (exists: %s-%s new: %s-%s)" % (name, dep_name, deps[dep_name]['version'], dep_name, dep_dict['version']))
            else:
                deps[dep_name] = dep_dict

    return deps


def create_build_project(name, meta, build_deps):
    project_dir = os.path.join(PROJECT_ROOT, 'nodejs-%s' % name)
    update = False
    try:
        os.makedirs(project_dir, 0755)
    except OSError as e:
        if e.errno == errno.EEXIST:
            warning("%s already exists; updating" % project_dir)
            update = True
        else:
            fatal(e)

    makefile = os.path.join(project_dir, 'Makefile')

    with open(makefile, 'w') as f:
        f.write('NAME\t\t:= %s\n' % name)
        f.write('VERSION\t\t:= %s\n' % meta['version'])
        shasum = meta['meta'].get('dist', {}).get('shasum', None)
        if shasum:
            f.write('SHA1SUM\t\t:= %s\n' % shasum)
        if build_deps:
            f.write('DEPENDENCIES\t:= %s\n' % " ".join(build_deps))
        f.write('\ninclude ../include/Makefile.rpm-from-npm\n')

    if update:
        print "Updated %s with %s-%s" % (makefile, name, meta['version'])
    else:
        print "Created %s for %s-%s" % (makefile, name, meta['version'])


def main():
    try:
        package_json_path = sys.argv[1]
    except IndexError:
        fatal("Must supply path/to/package.json")

    with open(package_json_path) as f:
        package_meta = json.load(f)

    deps = build_dependency_tree(package_meta)
    for dep, meta in deps.items():
        build_deps = []
        for build_dep in meta['meta'].get('dependencies', {}):
            build_deps.append(build_dep)
        #print "%s: %s" % (dep, meta['version'])
        create_build_project(dep, meta, build_deps)


if __name__ == '__main__':
    main()
