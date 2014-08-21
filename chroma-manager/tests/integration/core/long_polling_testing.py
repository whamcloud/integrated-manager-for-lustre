import logging
from threading import Thread

logger = logging.getLogger('long_polling')
logger.setLevel(logging.DEBUG)


class LongPollingThread(Thread):
    """
    Provide simple facilities to test long polling. Simply monitors an endpoint and
    counts the responses.
    """

    def __init__(self, test_uri, test_case):
        """

        :param endpoint: The end point to monitor
        :param test_case: Test case that provides endpoint functionality.
        """
        super(LongPollingThread, self).__init__()

        self.test_uri = test_uri
        self.test_case = test_case
        self.response_count = 0
        self.last_response = None
        self.error = None
        # for now use timestamp, should use the real mechanism, but to get running do the alternative.
        self.last_modified = 0
        self.exit = False

        self.start()

    def run(self):
        while not self.exit:
            try:
                self.last_response = self.test_case.get_json_by_uri(self.test_uri, {'last_modified': self.last_modified})
                self.last_modified = self.last_response['meta']['last_modified']
                self.response_count += 1
            except Exception as e:
                self.error = e
                break
