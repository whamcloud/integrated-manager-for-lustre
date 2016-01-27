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


from setuptools import setup, find_packages, findall
from scm_version import PACKAGE_VERSION
from re import sub

excludes = ["*docs*"]

setup(
    name = 'chroma-manager',
    version = PACKAGE_VERSION,
    author = "Intel Corporation",
    author_email = "hpdd-info@intel.com",
    url = 'http://lustre.intel.com/',
    license = 'Proprietary',
    description = 'The Intel Manager for Lustre Monitoring and Administration Interface',
    long_description = open('README.txt').read(),
    packages = find_packages(exclude=excludes) + [''],
    # include_package_data would be far more convenient, but the top-level
    # package confuses setuptools. As a ridiculous hackaround, we'll game
    # things by prepending a dot to top-level datafiles (which implies
    # file creation/cleanup in the Makefile) to deal with the fact
    # that setuptools wants to strip the first character off the filename.
    package_data = {
        '': [".chroma-manager.py", ".production_supervisord.conf", ".chroma-manager.conf.template", ".mime.types"],
        'chroma_core': ["fixtures/default_power_types_el6.json",
                        "fixtures/default_power_types_el7.json"],
        'chroma_ui': ["static/js/lib/*.js", "static/js/lib/angular/*.js",
                      "static/js/lib/select-box-it/select-box-it.js",
                      "static/js/lib/select-box-it/select-box-it.css",
                      "static/js/lib/sprintf/*.js", "static/js/*.js",
                      "static/js/app/*.js",
                      "static/js/controllers/*.js", "static/js/controllers/dialogs/*.js",
                      "static/js/directives/*.js", "static/js/directives/validators/*.js",
                      "static/js/filters/*.js", "static/js/interceptors/*.js",
                      "static/js/models/*.js",
                      "static/js/modules/exception/assets/css/*.css", "static/js/modules/exception/*.js",
                      "static/js/responsive/*.js",
                      "static/js/services/*.js",
                      "static/partials/*.html", "static/partials/dialogs/*.html",
                      "static/partials/directives/*.html",
                      "static/font/*", "static/css/font-awesome/*.css", "static/css/bootstrap/*.css",
                      "static/css/smoothness/images/*",
                      "static/css/smoothness/*.css", "static/css/images/*.gif",
                      "static/css/*.css", "static/images/fugue/*.png",
                      "static/images/datatables/*.png", "static/images/datatables/*.jpg",
                      "static/images/*.ico", "static/images/*.png",
                      "static/images/*.gif", "templates/*.html", "templates/new/*.html",
                      "static/chroma_ui/bower_components/font-awesome/fonts/*",
                      "static/chroma_ui/common/login/assets/images/*.png",
                      "static/chroma_ui/iml/app/assets/images/*",
                      "static/chroma_ui/styles/imports-*.css",
                      "static/chroma_ui/built-*.js", "static/chroma_ui/built-*.js.map",
                      "static/chroma_ui/bundle.js",
                      "static/chroma_ui/bundle.map.json"],
        'chroma_help': ["static/webhelp/*.htm*",
                        "static/webhelp/*.gif", "static/webhelp/*.js",
                        "static/webhelp/*.css", "static/webhelp/*.jpg",
                        "static/webhelp/*.png", "static/webhelp/*.swf"],
        'polymorphic': ["COPYING"],
        'tests': ["integration/run_tests", "integration/*/*.json", "sample_data/*"],
        'ui-modules': [
            "node_modules/intel-view-server/*.js",
            "node_modules/intel-view-server/lib/*.js",
            "node_modules/intel-view-server/middleware/*.js",
            "node_modules/intel-view-server/routes/*.js",
            "node_modules/intel-view-server/package.json",
            "node_modules/intel-realtime/*.js",
            "node_modules/intel-realtime/reverse-source-map/*.js",
            "node_modules/intel-realtime/serialize-error/*.js",
            "node_modules/intel-realtime/socket-router/*.js",
            "node_modules/intel-realtime/socket-router/middleware/*.js",
            "node_modules/intel-realtime/socket-router/routes/*.js",
            "node_modules/intel-realtime/package.json"
        ] + [sub(r'^ui-modules/', '', x) for x in findall('ui-modules/node_modules/intel-view-server/node_modules')]
          + [sub(r'^ui-modules/', '', x) for x in findall('ui-modules/node_modules/intel-realtime/node_modules')]
    },
    scripts = ["chroma-host-discover"],
    entry_points = {
        'console_scripts': [
            'chroma-config = chroma_core.lib.service_config:chroma_config',
            'chroma = chroma_cli.main:standard_cli'
        ]
    }
)
