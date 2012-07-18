import logging
import time

from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.utility_testcase import UtilityTestCase

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.FileHandler('test.log'))


class ApiTestCase(UtilityTestCase):
    """
    Adds set of convenience functions for interacting with the chroma api.
    """

    def wait_for_command(self, chroma_manager, command_id, timeout=TEST_TIMEOUT, verify_successful=True):
        logger.debug("wait_for_command %s" % command_id)
        # TODO: More elegant timeout?
        running_time = 0
        command_complete = False
        while running_time < timeout and not command_complete:
            response = chroma_manager.get(
                '/api/command/%s/' % command_id,
            )
            self.assertTrue(response.successful, response.text)
            command = response.json
            command_complete = command['complete']
            if not command_complete:
                time.sleep(1)
                running_time += 1

        self.assertTrue(command_complete, command)
        if verify_successful and (command['errored'] or command['cancelled']):
            print "COMMAND %s FAILED:" % command['id']
            print "-----------------------------------------------------------"
            print command
            print ''

            for job_uri in command['jobs']:
                response = chroma_manager.get(job_uri)
                self.assertTrue(response.successful, response.text)
                job = response.json
                if job['errored']:
                    print "Job %s Errored:" % job['id']
                    print job
                    print ''
                    for step_uri in job['steps']:
                        response = chroma_manager.get(step_uri)
                        self.assertTrue(response.successful, response.text)
                        step = response.json
                        if step['exception'] and not step['exception'] == 'None':
                            print "Step %s Errored:" % step['id']
                            print step['console']
                            print step['exception']
                            print step['backtrace']
                            print ''

            self.assertFalse(command['errored'] or command['cancelled'], command)

    def wait_for_commands(self, chroma_manager, command_ids, timeout=TEST_TIMEOUT, verify_successful = True):
        for command_id in command_ids:
            self.wait_for_command(chroma_manager, command_id, timeout, verify_successful)

    def get_list(self, url, args = {}):
        response = self.chroma_manager.get(url, params = args)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json['objects']

    def get_by_uri(self, uri):
        response = self.chroma_manager.get(uri)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json

    def set_state(self, uri, state):
        logger.debug("set_state %s %s" % (uri, state))
        object = self.get_by_uri(uri)
        object['state'] = state

        response = self.chroma_manager.put(uri, body = object)
        if response.status_code == 204:
            logger.warning("set_state %s %s - no-op" % (uri, state))
        else:
            self.assertEquals(response.status_code, 202, response.content)
            self.wait_for_command(self.chroma_manager, response.json['command']['id'])

        self.assertState(uri, state)

    def assertNoAlerts(self, uri):
        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertNotIn(uri, [a['alert_item'] for a in alerts])

    def assertHasAlert(self, uri):
        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertIn(uri, [a['alert_item'] for a in alerts])

    def assertState(self, uri, state):
        logger.debug("assertState %s %s" % (uri, state))
        obj = self.get_by_uri(uri)
        self.assertEqual(obj['state'], state)

    def get_filesystem(self, filesystem_id):
        return self.get_by_uri("/api/filesystem/%s/" % filesystem_id)
