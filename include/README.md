# module-tools
Tools to work with and build modules

This module can be included as a [git subrepo](https://github.com/ingydotnet/git-subrepo), imported at ``include/` in an enclosing module to provide tools to help build RPMs for the enclosing module.

See the writeup for the [Basics of git subrepo](https://github.com/ingydotnet/git-subrepo/wiki/Basics).

Once this module is imported to an enclosing module, the enclosing module needs a Makefile defining the enclosing module's *NAME* and optionally *PACKAGE_VERSION*, *DIST_VERSION*, *PACKAGE_RELEASE*, *TEST_DEPS* and include a _Makefile_ fragment indicating what type of package it is.  Choices for example are *python-localsrc.mk* for a Python package with source local to the module.  *python-pypi.mk* is used for a Python module that will be built from it's PyPI release.

Some of the useful make targets provided are:
- githooks: Installs the hooks/ subdirectory into your git repo as it
            git hooks
- rpms: Creates all of the binary RPMs for the module
- srpm: Creates the source RPM for the module
- build_test: Performs an RPM build in mock
- test: Runs any tests of the module
- tag: Generates any needed files and applies a git tag
- copr_build: Submits the RPM specfile to Copr for building in a
              private repo
              - this requires that a file named copr-local.mk exists
                in the repo with COPR_OWNER and COPR_PROJECT defined
                as the owner and project in Copr to build in
- iml_copr_repo: Submits the RPM specfile to Corp for building in
                 the production IML repo

