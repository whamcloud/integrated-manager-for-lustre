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


"""
To acquire a log, use `log_register('foo')`.  'foo' is just prepended
to the start of log lines, rather than being used as the filename.  Filename
is determined usually by the service name when running within `chroma_service`.

The intention is that there is a log file per container process, and logs from
a particular module will go to the log of whatever process they are running
within, prefaced with the subsystem name.

Outside of `chroma_service`, use `log_set_filename` to set the filename, or
`log_enable_stdout` to output all logs to standard out.

`settings.LOG_PATH` and `settings.LOG_LEVEL` control the global directory
and level for logging.
"""


import logging
from logging.handlers import WatchedFileHandler, MemoryHandler
import os
import settings


_log_filename = None
_loggers = set()
_enable_stdout = False
trace = None

FILE_FORMAT = '[%(asctime)s: %(levelname)s/%(name)s] %(message)s'
#  Alternative file format showing files and line numbers
#FILE_FORMAT = '[%(asctime)s: %(thread)d %(pathname)s:%(lineno)d %(levelname)s/%(name)s] %(message)s'
STDOUT_FORMAT = '[%(asctime)s: %(levelname)s/%(name)s] %(message)s'


def _add_file_handler(logger, filename=None):
    if not _has_handler(logger, WatchedFileHandler):
        if filename is None:
            filename = _log_filename
        handler = WatchedFileHandler(filename)
        handler.setFormatter(logging.Formatter(FILE_FORMAT))
        logger.addHandler(handler)


def _add_stream_handler(logger):
    if not _has_handler(logger, logging.StreamHandler):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(STDOUT_FORMAT))
        logger.addHandler(handler)


def _has_handler(logger, handler_class):
    for handler in logger.handlers:
        if isinstance(handler, handler_class):
            return True
    return False


def log_set_filename(filename):
    """
    Set the output file for all loggers within this process.
    :param filename: Basename for the log (will be prefixed with settings.LOG_PATH)
    :return: None
    """
    global _log_filename
    if _log_filename:
        assert _log_filename == filename
    _log_filename = os.path.join(settings.LOG_PATH, filename)

    # Explicit file creation here so that we don't wait until first message
    # to pick up a permissions problem.
    if not os.path.exists(_log_filename):
        open(_log_filename, 'a').close()

    for logger in _loggers:
        _add_file_handler(logger)


def log_enable_stdout():
    """
    Start echoing all logs in this process to standard out

    :return: None
    """
    global _enable_stdout
    _enable_stdout = True
    for logger in _loggers:
        _add_stream_handler(logger)


def log_disable_stdout():
    """
    Stop echoing all logs in this process to standard out

    :return: None
    """
    global _enable_stdout
    _enable_stdout = False
    for logger in _loggers:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                logger.removeHandler(handler)


def custom_log_register(log_name, filename=None):
    """Create another custom log handler to an optional file

    logger can have a file handler, or no handler at all.  In the second case
    you can then add your own handlers after the call to this method.

    Uses settings.LOG_LEVEL

    Be aware that the user that calls this method will own the log file.  Or the file
    may be created in some other manner owned by anyone.
    If any other process then tries to register this same log file it may not be
    able to read/write, and an IOError will be raised.  That is left uncaught, because
    it's a siutation you shouldn't leave unchecked in your calling code.
    """

    logger = logging.getLogger(log_name)
    logger.setLevel(settings.LOG_LEVEL)

    # If a filename is requested for this logger,
    # make sure it will be created in the right place.
    if filename:
        if not filename.startswith(settings.LOG_PATH):
            filename = os.path.join(settings.LOG_PATH, filename)

        # NB: this will fail if the permissions prevent opening the file.
        # Generally just make sure the user (process) creating the file is
        # the same one that will write to it.
        _add_file_handler(logger, filename)

    _loggers.add(logger)
    return logger


def log_register(log_name):
    """
    Acquire a logger object, initialized with the global level and output options

    :param log_name: logger name (as in `logging.getLogger`), will be prefixed to log lines
    :return: A `logging.Logger` instance.
    """
    logger = logging.getLogger(log_name)
    logger.setLevel(settings.LOG_LEVEL)

    if _enable_stdout:
        _add_stream_handler(logger)
    if _log_filename:
        _add_file_handler(logger)
    if not _log_filename and not _enable_stdout:
        # Prevent 'No handlers could be found' spam
        logger.addHandler(MemoryHandler(0))

    _loggers.add(logger)
    return logger
