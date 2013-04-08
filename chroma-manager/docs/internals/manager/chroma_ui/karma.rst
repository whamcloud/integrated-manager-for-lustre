Karma JavaScript Test Runner
----------------------------

Introduction
____________

Karma is an easy way to run your JavaScript tests.
It allows you to setup and run tests on multiple browsers simultaneously.
Tests can be repeatedly run on save; or as a single run.

Setup (Steps 1 and 2 can be skipped if already performed)
_________________________________________________________

1. Install nodejs:

  ::

    ~$ brew install node

2. Add the https-proxy config to npm:

  ::

    # Assuming you have the https_proxy environment variable set, and that it doesn't begin with http://
    ~$ npm config set https-proxy "http://$https_proxy"

3. Install karma:

  ::

    ~$ npm install -g karma


Configuration
__________________

Karma can be configured via the karma.conf.js file. Some interesting conf parameters are:

  ::

    browsers {Array} (A list of browsers to simultaneously run tests in.)

    singlerun {Boolean} (Whether karma should continuously run tests.)

    reporter {Array} (A list of reporters to use for output. There are options here for junit, coverage, and growl notifications.)

    files {Array} (A list of adapters / files to load for testing. Paths can be glob patterns.)

  .. note::

    These are just high level options. For more in depth configuration please refer to the
    karma configuration_:

.. _configuration: http://karma-runner.github.com/0.8/config/files.html

Use in development
__________________

::

  chroma_ui$ karma start

This will start karma for a test run. Depending on the singlerun parameter in your karma.conf.js file, the runner may
keep running to watch files, or it may terminate after a single run.

Notes
__________________

- Karma documentation can be found here_.
- Karma used to be named Testacular, keep that in mind when googling.

.. _here: http://karma-runner.github.com/

