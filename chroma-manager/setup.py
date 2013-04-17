#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from setuptools import setup, find_packages
from scm_version import PACKAGE_VERSION

excludes = ["*docs*", "*r3d*tests*"]

setup(
    name = 'chroma-manager',
    version = PACKAGE_VERSION,
    author = "Whamcloud, Inc.",
    author_email = "info@whamcloud.com",
    url = 'http://www.whamcloud.com/',
    license = 'Proprietary',
    description = 'The Whamcloud Lustre Monitoring and Adminisration Interface',
    long_description = open('README.txt').read(),
    packages = find_packages(exclude=excludes) + [''],
    # include_package_data would be far more convenient, but the top-level
    # package confuses setuptools. As a ridiculous hackaround, we'll game
    # things by prepending a dot to top-level datafiles (which implies
    # file creation/cleanup in the Makefile) to deal with the fact
    # that setuptools wants to strip the first character off the filename.
    package_data = {
        '': [".chroma-manager.wsgi", ".production_supervisord.conf"],
        'chroma_ui': ["static/js/lib/*.js", "static/js/lib/angular/*.js", "static/js/*.js",
                      "static/js/controllers/*.js", "static/js/filters/*.js", "static/js/interceptors/*.js",
                      "static/js/models/*.js", "static/js/services/*.js", "static/js/util/sprintf/*.js",
                      "static/partials/*.html", "static/fonts/*", "static/css/bootstrap/*.css",
                      "static/css/smoothness/images/*",
                      "static/css/smoothness/*.css", "static/css/images/*", "static/css/*.css",
                      "static/images/fugue/*.png",
                      "static/images/datatables/*.png", "static/images/datatables/*.jpg",
                      "static/images/breadcrumb/*.gif", "static/images/breadcrumb/COPYING",
                      "static/images/*.ico", "static/images/*.png",
                      "static/images/*.gif", "templates/*"],
        'chroma_help': ["static/contextual/*.html", "static/webhelp/*.htm*",
                        "static/webhelp/*.gif", "static/webhelp/*.js",
                        "static/webhelp/*.css", "static/webhelp/*.jpg",
                        "static/webhelp/*.png", "static/webhelp/*.swf"],
        'polymorphic': ["COPYING"],
        'tests': ["integration/run_tests", "integration/*/*.json", "sample_data/*"],
    },
    scripts = ["chroma-host-discover"],
    entry_points = {
        'console_scripts': [
            'chroma-config = chroma_core.lib.service_config:chroma_config',
            'chroma = chroma_cli.main:standard_cli'
        ]
    }
)
