from collections import defaultdict

import mock

from chroma_core.lib.cache import ObjectCache
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from tests.unit.chroma_api.tastypie_test import ResourceTestCase
from tests.unit.chroma_core.helpers import synthetic_volume_full
from chroma_core.models import ManagedTarget


class ChromaApiTestCase(ResourceTestCase):
    """
    Unit tests which drive the *Resource classes in chroma_api/
    """

    def __init__(self, methodName=None, username="admin", password="lustre"):
        super(ChromaApiTestCase, self).__init__(methodName=methodName)
        self.username = username
        self.password = password

    def setUp(self):
        super(ChromaApiTestCase, self).setUp()
        from chroma_api.authentication import CsrfAuthentication

        self.old_is_authenticated = CsrfAuthentication.is_authenticated
        CsrfAuthentication.is_authenticated = mock.Mock(return_value=True)

        self.assertTrue(self.api_client.client.login(username=self.username, password=self.password))

        from tests.unit.chroma_core.helpers import load_default_profile

        load_default_profile()

        # If the test that just ran imported storage_plugin_manager, it will
        # have instantiated its singleton, and created some DB records.
        # Django TestCase rolls back the database, so make sure that we
        # also roll back (reset) this singleton.
        import chroma_core.lib.storage_plugin.manager

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = (
            chroma_core.lib.storage_plugin.manager.StoragePluginManager()
        )

        #  Fetching available transitions from the JobSchedule would require
        #  Avoiding moving this to integration scope by mocking the rpc
        #  fetched method.

        @classmethod
        def fake_available_transitions(cls, object_list):
            transitions = defaultdict(list)
            for obj_ct, obj_id in object_list:
                obj = JobScheduler._retrieve_stateful_object(obj_ct, obj_id)
                #  fake receiving ['fake_trans', 'make_fake_trans'] from JS
                #  and converting to this form with verbs
                transitions[obj.id] = [
                    {"state": "fake_trans", "verb": "make_fake_trans"},
                    {"state": "fake_other", "verb": "make_fake_other"},
                ]
            return transitions

        from chroma_core.services.job_scheduler import job_scheduler_client

        self.old_available_transitions = job_scheduler_client.JobSchedulerClient.available_transitions
        job_scheduler_client.JobSchedulerClient.available_transitions = fake_available_transitions

        @classmethod
        def fake_available_jobs(cls, object_list):
            jobs = defaultdict(list)
            for obj_ct, obj_id in object_list:
                obj = JobScheduler._retrieve_stateful_object(obj_ct, obj_id)
                jobs[obj.id] = []
            return jobs

        self.old_available_jobs = job_scheduler_client.JobSchedulerClient.available_jobs
        job_scheduler_client.JobSchedulerClient.available_jobs = fake_available_jobs

        @classmethod
        def fake_get_locks(cls, obj_key, obj_id):
            return {"read": [1, 2], "write": [3, 4]}

        self.old_get_locks = job_scheduler_client.JobSchedulerClient.get_locks
        job_scheduler_client.JobSchedulerClient.get_locks = fake_get_locks

    def tearDown(self):
        from chroma_api.authentication import CsrfAuthentication

        CsrfAuthentication.is_authenticated = self.old_is_authenticated

        #  Restore
        from chroma_core.services.job_scheduler import job_scheduler_client

        job_scheduler_client.JobSchedulerClient.available_transitions = self.old_available_transitions
        job_scheduler_client.JobSchedulerClient.available_jobs = self.old_available_jobs

        ObjectCache.clear()

    def api_set_state_full(self, uri, state):
        original_object = self.api_get(uri)
        original_object["state"] = state
        response = self.api_client.put(uri, data=original_object)
        try:
            self.assertHttpAccepted(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))
        self.assertHttpAccepted(response)

    def api_set_state_partial(self, uri, state):
        response = self.api_client.put(uri, data={"state": state})
        try:
            self.assertHttpAccepted(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))

    def api_get(self, uri):
        response = self.api_client.get(uri)
        try:
            self.assertHttpOK(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))
        return self.deserialize(response)

    def api_post(self, uri, data=None, assertion_test=lambda self, response: self.assertHttpAccepted(response)):
        response = self.api_client.post(uri, data=data)
        try:
            assertion_test(self, response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))
        return self.deserialize(response)

    def create_simple_filesystem(self, host):
        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem, ManagedTargetMount

        self.mgt, _ = ManagedMgs.create_for_volume(synthetic_volume_full(host).id, name="MGS")
        self.fs = ManagedFilesystem.objects.create(mgs=self.mgt, name="testfs")
        ObjectCache.add(ManagedFilesystem, self.fs)
        ObjectCache.add(ManagedTarget, ManagedTarget.objects.get(id=self.mgt.id))

        self.mdt, _ = ManagedMdt.create_for_volume(synthetic_volume_full(host).id, filesystem=self.fs)
        self.ost, _ = ManagedOst.create_for_volume(synthetic_volume_full(host).id, filesystem=self.fs)
        ObjectCache.add(ManagedTarget, ManagedTarget.objects.get(id=self.mdt.id))
        ObjectCache.add(ManagedTarget, ManagedTarget.objects.get(id=self.ost.id))
        ObjectCache.add(ManagedTargetMount, ManagedTargetMount.objects.get(target_id=self.mgt.id))
        ObjectCache.add(ManagedTargetMount, ManagedTargetMount.objects.get(target_id=self.mdt.id))
        ObjectCache.add(ManagedTargetMount, ManagedTargetMount.objects.get(target_id=self.ost.id))

    def api_get_list(self, uri, **kwargs):
        response = self.api_client.get(uri, **kwargs)
        try:
            self.assertHttpOK(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))
        return self.deserialize(response)["objects"]

    def api_patch_attributes(self, uri, attributes):
        response = self.api_client.patch(uri, data=attributes)
        try:
            self.assertHttpAccepted(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))

    def spider_api(self):
        ObjectCache.clear()

        from chroma_api.urls import api

        xs = filter(lambda x: x[0] != "action", api._registry.items())
        xs = filter(lambda x: "get" in x[1]._meta.list_allowed_methods, xs)

        for _, resource in xs:
            list_uri = resource.get_resource_uri()
            response = self.api_client.get(list_uri, data={"limit": 0})
            self.assertEqual(
                response.status_code, 200, "%s: %s %s" % (list_uri, response.status_code, self.deserialize(response))
            )
            if "get" in resource._meta.detail_allowed_methods:
                objects = self.deserialize(response)["objects"]

                for object in objects:
                    # Deal with the newer bulk data format, if it is in that format.
                    if ("resource_uri" not in object) and ("traceback" in object) and ("error" in object):
                        del object["traceback"]
                        del object["error"]
                        self.assertEqual(len(object), 1)
                        object = object.values()[0]

                    response = self.api_client.get(object["resource_uri"])
                    self.assertEqual(
                        response.status_code,
                        200,
                        "resource_url: %s, %s %s %s"
                        % (object["resource_uri"], response.status_code, self.deserialize(response), object),
                    )
