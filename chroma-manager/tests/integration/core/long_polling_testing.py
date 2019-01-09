import time
import logging
from threading import Thread

logger = logging.getLogger("long_polling")
logger.setLevel(logging.DEBUG)

# Long poll timeout Seconds - be nice to get this from settings but they are not available to the integration tests
LONG_POLL_TIMEOUT_SECONDS = 60 * 5


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
        self.responses = []
        self.error = None
        # for now use timestamp, should use the real mechanism, but to get running do the alternative.
        self.last_modified = 0
        self.exit = False

        self.start()

    def run(self):
        while not self.exit:
            try:
                request_time = time.time()
                response = self.test_case.get_by_uri(
                    self.test_uri, args={"last_modified": self.last_modified, "limit": 0}, verify_successful=False
                )

                if response.status_code == 200:
                    self.last_modified = response.json["meta"]["last_modified"]
                    self.responses.append(response)
                elif response.status_code == 304:  # 304 Not Modified
                    assert (
                        time.time() - request_time
                    ) >= LONG_POLL_TIMEOUT_SECONDS, "Endpoint responded with 304 before long polling timeout"
                else:
                    raise Exception(
                        "Unexpected return code %s\nresponse %s" % (response.status_code, response._content)
                    )
            except Exception as e:
                self.error = e
                logger.warning("LongPollingThread exited unexpectedly with %s" % e)
                break

    @property
    def response_count(self):
        return len(self.responses)

    def __repr__(self):
        return ("Endpoint {0}\n" "Count {1}\n" "Responses: {2}\n" "Current: {3}").format(
            self.test_uri,
            self.response_count,
            "\n".join([response._content for response in self.responses]),
            self.test_case.get_by_uri(self.test_uri, args={"limit": 0}, verify_successful=False),
        )
