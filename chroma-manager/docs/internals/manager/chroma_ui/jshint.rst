JSHint Setup
------------

Introduction
____________

JSHint is a code quality and style tool that can be run via the command line.
Integration with PyCharm is also available.

Setup (Steps 1 and 2 can be skipped if already performed)
_________________________________________________________

1. Install nodejs:

  ::

    ~$ brew install node

2. Add the https-proxy config to npm:

  ::

    # Assuming you have the https_proxy environment variable set, and that it doesn't begin with http://
    ~$ npm config set https-proxy "http://$https_proxy"

3. Install jshint:

  ::

    ~$ npm install -g jshint


PyCharm Integration
___________________

From the PyCharm menu item do: Select Preferences -> Expand JavaScript -> Expand Code Quality Tools -> Select JSHint -> Check Enable, Check Use Config, Set the version
drop-down to r12.

Now your .js files will be validated using the rules in the .jshintrc file at the root project directory.

.. image:: ../media/jshint_setup.png


Pre-Commit Integration
______________________

Any new work will be subject to a pre-commit jshint check if jshint is installed. New work currently constitutes any
subdir under chroma_ui/static/js excluding the lib dir. app.js / constants.js under chroma_ui/static/js are also included.
