import Queue
import json
import random
import string
import requests
import datetime

from chroma_core.lib.util import chroma_settings
settings = chroma_settings()


class AgentHttpClient(object):
    """
    GET/POST operations in the style that AgentClient would do them, for impersonating the agent.
    """
    URL = "http://localhost:%s/agent/message/" % settings.HTTP_AGENT_PORT
    CLIENT_NAME = 'myserver'

    def __init__(self):
        self.client_start_time = datetime.datetime.now().isoformat() + 'Z'
        self.server_boot_time = datetime.datetime.now().isoformat() + 'Z'

        # Serial must be different every time because once we use it in a test it is permanently
        # revoked.
        self.CLIENT_CERT_SERIAL = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        self.headers = {
            "Accept": "application/json",
            "Content-type": "application/json",
            "X-SSL-Client-Name": self.CLIENT_NAME,
            "X-SSL-Client-Serial": self.CLIENT_CERT_SERIAL
        }

        # Whenever we GET, we will may get more messages than we
        # expect: stash them here for the next caller
        self._tx_messages = Queue.Queue()

    def _post(self, messages):
        post_body = {
            'server_boot_time': self.server_boot_time,
            'client_start_time': self.client_start_time,
            'messages': messages
        }
        return requests.post(self.URL, data=json.dumps(post_body), headers=self.headers)

    def _get(self):
        get_params = {'server_boot_time': self.server_boot_time, 'client_start_time': self.client_start_time}
        return requests.get(self.URL, headers=self.headers, params=get_params)

    def _receive_messages(self, required_messages=1, allow_extras=False):
        """

        :param required_messages: How many messages to acquire before returning.  If cannot get this
                                  many then raise exception.
        :param allow_extras: If false, raise an exception if GET returns more than required_messages
        :return: List of dicts
        """
        messages = []
        while len(messages) < required_messages:
            try:
                messages.append(self._tx_messages.get_nowait())
            except Queue.Empty:
                break

        # Do a GET if we didn't already have enough messages
        if len(messages) < required_messages:
            response = self._get()
            remaining_messages = required_messages - len(messages)
            messages.extend(response.json()['messages'][0:remaining_messages])
            if not allow_extras and len(response.json()['messages']) > remaining_messages:
                raise RuntimeError("Too many messages in GET: %s" % response.json()['messages'])

            for extra_message in response.json()['messages'][remaining_messages:]:
                self._tx_messages.put(extra_message)

        if len(messages) != required_messages:
            raise RuntimeError("Failed to receive %s messages, got: %s" % (required_messages, messages))

        return messages

    def _mock_restart(self):
        self.client_start_time = datetime.datetime.now().isoformat() + 'Z'
