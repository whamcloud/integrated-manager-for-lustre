import logging
import os
import sys
import threading
import time


chroma_logger = logging.getLogger("test")
chroma_logger.setLevel(logging.DEBUG)


try:
    import nose

    nose_installed = True
except ImportError:
    nose_installed = False


if nose_installed:

    # Monkey patch TextTestResult to print errors as they occur

    def monkeyPatchedAddError(self, test, err):
        super(nose.result.TextTestResult, self).addError(test, err)
        if self.showAll:
            self.stream.writeln("ERROR")
            self.stream.writeln(self._exc_info_to_string(err, test))
            chroma_logger.error(self._exc_info_to_string(err, test))
        elif self.dots:
            self.stream.write("E")
            self.stream.flush()

    def monkeyPatchedAddFailure(self, test, err):
        super(nose.result.TextTestResult, self).addFailure(test, err)
        if self.showAll:
            self.stream.writeln("FAIL")
            self.stream.writeln(self._exc_info_to_string(err, test))
            chroma_logger.error(self._exc_info_to_string(err, test))
        elif self.dots:
            self.stream.write("F")
            self.stream.flush()

    nose.result.TextTestResult.chroma_logger = chroma_logger
    nose.result.TextTestResult.addError = monkeyPatchedAddError
    nose.result.TextTestResult.addFailure = monkeyPatchedAddFailure

    # Monkey patch TextTestRunner to exit hard if there are hanging threads

    def monkeyPatchedRun(self, test):
        self.descriptions = 0
        threads_at_beginning_of_test_run = threading.enumerate()
        chroma_logger.info("Starting tests with these threads running: '%s'" % threads_at_beginning_of_test_run)

        wrapper = self.config.plugins.prepareTest(test)
        if wrapper is not None:
            test = wrapper

        wrapped = self.config.plugins.setOutputStream(self.stream)
        if wrapped is not None:
            self.stream = wrapped

        result = self._makeResult()
        start = time.time()
        test(result)
        stop = time.time()
        result.printErrors()
        result.printSummary(start, stop)
        self.config.plugins.finalize(result)

        def get_hanging_threads():
            ending_threads = threading.enumerate()

            hanging_threads = []
            for thread in ending_threads:
                if thread not in threads_at_beginning_of_test_run and thread.is_alive():
                    hanging_threads.append(thread)

            return hanging_threads

        # Give the threads some time to stop
        running_time = 0
        while running_time < 300 and get_hanging_threads():
            time.sleep(5)
            running_time += 5

        chroma_logger.info("Ending tests with these threads running: '%s'" % threading.enumerate())
        hanging_threads = get_hanging_threads()
        if hanging_threads:
            sys.stderr.write(
                "\n********************\n\nTERMINATING TEST RUN - NOT ALL THREADS STOPPED AT END OF TESTS: '%s'\n\n********************\n"
                % hanging_threads
            )
            os._exit(1)

        return result

    nose.core.TextTestRunner.chroma_logger = chroma_logger
    nose.core.TextTestRunner.run = monkeyPatchedRun
