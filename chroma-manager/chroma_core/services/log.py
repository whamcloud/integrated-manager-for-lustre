#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


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

FILE_FORMAT = '[%(asctime)s: %(levelname)s/%(name)s] %(message)s'
STDOUT_FORMAT = '[%(asctime)s: %(levelname)s/%(name)s] %(message)s'


def _add_file_handler(logger):
    if not _has_handler(logger, WatchedFileHandler):
        handler = WatchedFileHandler(_log_filename)
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
    assert not _log_filename
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
