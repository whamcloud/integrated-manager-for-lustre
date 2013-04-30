import logging
import os
import sys
import threading
import time


logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


def setUpPackage():
    global threads_at_beginning_of_test_run
    threads_at_beginning_of_test_run = threading.enumerate()
    logger.info("Starting tests with these threads running: '%s'" % threads_at_beginning_of_test_run)


def tearDownPackage():
    # Give the threads some time to stop
    running_time = 0
    while running_time < 300 and get_hanging_threads():
        time.sleep(5)
        running_time += 5

    logger.info("Ending tests with these threads running: '%s'" % threading.enumerate())
    hanging_threads = get_hanging_threads()
    if hanging_threads:
        sys.stderr.write("\n********************\n\nTERMINATING TEST RUN - NOT ALL THREADS STOPPED AT END OF TESTS: '%s'\n\n********************\n" % hanging_threads)
        os._exit(1)


def get_hanging_threads():
    ending_threads = threading.enumerate()

    hanging_threads = []
    for thread in ending_threads:
        if thread not in globals().get('threads_at_beginning_of_test_run', []) and thread.is_alive():
            hanging_threads.append(thread)

    return hanging_threads
