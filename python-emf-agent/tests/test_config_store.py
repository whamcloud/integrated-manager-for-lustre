import os
import tempfile
import shutil
import threading
import multiprocessing
import time
from mock import patch

import unittest

from chroma_agent.config_store import (
    ConfigStore,
    ConfigKeyExistsError,
    InvalidConfigIdentifier,
)


class ConfigStoreTests(unittest.TestCase):
    def setUp(self):
        super(ConfigStoreTests, self).setUp()

        self.config = ConfigStore(tempfile.mkdtemp())

        self.data = {
            "foo": 1,
            "bar": "1",
            "baz": ["qux", "quux", "corge"],
            "grault": {"garply": "waldo", "fred": ["plugh", "xyzzy"]},
            "thud": False,
        }

    def tearDown(self):
        super(ConfigStoreTests, self).tearDown()

        shutil.rmtree(self.config.path)

    def test_set(self):
        self.config.set("barfy", "cow", self.data)
        self.assertEqual(self.data, self.config.get("barfy", "cow"))

        with self.assertRaises(ConfigKeyExistsError):
            self.config.set("barfy", "cow", self.data)

    def test_update(self):
        self.config.set("barfy", "cow", self.data)

        self.data["thud"] = True
        self.config.update("barfy", "cow", self.data)
        self.assertEqual(self.data, self.config.get("barfy", "cow"))

    def test_delete(self):
        self.config.set("barfy", "cow", self.data)

        self.config.delete("barfy", "cow")
        with self.assertRaises(KeyError):
            self.config.get("barfy", "cow")

    def test_delete_idempotent(self):
        # Shouldn't fail -- if it's not there, then the intended goal
        # was accomplished.
        self.config.delete("barfy", "cow")

    def test_delete_section(self):
        self.config.set("barfy", "cow", self.data)

        self.config.delete_section("barfy")
        with self.assertRaises(TypeError):
            self.config.get("barfy", "cow")

    def test_get_nonexistent_section(self):
        self.assertListEqual([], self.config.get_section_keys("foo"))
        self.assertDictEqual({}, self.config.get_section("foo"))

    def test_sections(self):
        maladies = ["barfy", "gassy", "sad", "grumpy"]
        for malady in maladies:
            self.config.set(malady, "cow", self.data)

        self.assertListEqual(sorted(maladies), self.config.sections)

    def test_get_section(self):
        self.config.set("barfy", "cow", self.data)

        self.assertDictEqual({"cow": self.data}, self.config.get_section("barfy"))

    def test_get_all(self):
        maladies = ["barfy", "gassy", "sad", "grumpy"]
        for malady in maladies:
            self.config.set(malady, "cow", self.data)

        self.assertDictEqual(
            {
                "barfy": {"cow": self.data},
                "gassy": {"cow": self.data},
                "sad": {"cow": self.data},
                "grumpy": {"cow": self.data},
            },
            self.config.get_all(),
        )

    def test_clear(self):
        maladies = ["barfy", "gassy", "sad", "grumpy"]
        for malady in maladies:
            self.config.set(malady, "cow", self.data)

        self.config.clear()
        self.assertListEqual([], self.config.sections)

    def test_bad_identifiers(self):
        badkey = object()
        with self.assertRaises(InvalidConfigIdentifier):
            self.config.set("whoops", badkey, "foobar")
        with self.assertRaises(InvalidConfigIdentifier):
            self.config.set(badkey, "whoops", "foobar")

    def test_unicode_identifiers(self):
        test_id = u"should work"
        self.config.set("ok", test_id, self.data)
        self.assertDictEqual(self.data, self.config.get("ok", test_id))
        self.config.set(test_id, "ok", self.data)
        self.assertDictEqual(self.data, self.config.get(test_id, "ok"))

    def test_thread_safety(self):
        import Queue

        config = self.config
        data = self.data
        testcase = self
        exceptions = Queue.Queue()

        class ThreadA(threading.Thread):
            def __init__(self):
                super(ThreadA, self).__init__()
                self.config = config
                self.data = data
                self.testcase = testcase

            def run(self):
                try:
                    with self.config.lock:
                        self.config.set("barfy", "cow", self.data)
                        time.sleep(1)
                        self.testcase.assertDictEqual(self.data, self.config.get("barfy", "cow"))
                except Exception as e:
                    exceptions.put(e)

        class ThreadB(threading.Thread):
            def __init__(self):
                super(ThreadB, self).__init__()
                self.config = config

            def run(self):
                try:
                    self.config.clear()
                except Exception as e:
                    exceptions.put(e)

        a = ThreadA()
        b = ThreadB()
        self.assertEqual(a.config, b.config)

        a.start()
        b.start()

        a.join()
        b.join()

        with self.assertRaises(Queue.Empty):
            raise RuntimeError("Thread safety check failed: %s" % exceptions.get(block=False))

    def test_multiprocess_safety(self):
        from multiprocessing import Queue
        from Queue import Empty

        config = self.config
        data = self.data
        testcase = self
        exceptions = Queue()

        class ProcessA(multiprocessing.Process):
            def __init__(self):
                super(ProcessA, self).__init__()
                self.config = config
                self.data = data
                self.testcase = testcase

            def run(self):
                try:
                    with self.config.lock:
                        self.config.set("barfy", "cow", self.data)
                        time.sleep(1)
                        self.testcase.assertDictEqual(self.data, self.config.get("barfy", "cow"))
                except Exception as e:
                    exceptions.put(e)

        class ProcessB(multiprocessing.Process):
            def __init__(self):
                super(ProcessB, self).__init__()
                self.config = config

            def run(self):
                try:
                    self.config.clear()
                except Exception as e:
                    exceptions.put(e)

        a = ProcessA()
        b = ProcessB()
        self.assertEqual(a.config, b.config)

        a.start()
        b.start()

        a.join()
        b.join()

        with self.assertRaises(Empty):
            raise RuntimeError("Multi-process safety check failed: %s" % exceptions.get(block=False))

    def test_profile_managed_true(self):
        self.config.set("settings", "profile", {"managed": True})
        self.assertEqual(self.config.profile_managed, True)

    def test_profile_managed_false(self):
        self.config.set("settings", "profile", {"managed": False})
        self.assertEqual(self.config.profile_managed, False)

    def test_profile_managed_missing_false_section(self):
        self.assertEqual(self.config.profile_managed, False)

    def test_profile_managed_missing_false_ket(self):
        self.config.set("settings", "profile", {"trevor": "andy"})
        self.assertEqual(self.config.profile_managed, False)


class AgentStoreConversionTests(unittest.TestCase):
    def setUp(self):
        super(AgentStoreConversionTests, self).setUp()

        self.env_path_patch = patch("chroma_agent.conf.ENV_PATH", new=tempfile.mkdtemp())
        self.env_path = self.env_path_patch.start()
        self.config = ConfigStore(tempfile.mkdtemp())

    def tearDown(self):
        super(AgentStoreConversionTests, self).tearDown()

        self.env_path_patch.stop()
        shutil.rmtree(self.env_path)
        shutil.rmtree(self.config.path)

    def _create_agentstore_config(self):
        import uuid
        import json
        import string

        self.old_server_conf = {"url": "http://foo.bar.baz/"}

        with open(os.path.join(self.config.path, "server_conf"), "w") as f:
            json.dump(self.old_server_conf, f)

        self.old_target_configs = {}
        for i in xrange(0, 15):
            bdev = "/dev/sd%s" % string.ascii_lowercase[i]
            mntpt = "/mnt/target%04d" % i
            uuid_str = str(uuid.uuid4())
            target_config = dict(bdev=bdev, mntpt=mntpt)
            with open(os.path.join(self.config.path, uuid_str), "w") as f:
                json.dump(target_config, f)
            self.old_target_configs[uuid_str] = target_config

    def test_agentstore_conversion(self):
        with patch("chroma_agent.action_plugins.settings_management.config", new=self.config):
            self._create_agentstore_config()

            from chroma_agent.action_plugins.settings_management import (
                _convert_agentstore_config,
            )

            _convert_agentstore_config()

            with open(os.path.join(self.env_path, "manager-url.conf"), "r") as f:
                self.assertEqual(
                    f.read(),
                    "EMF_MANAGER_URL={}\n".format(self.old_server_conf.get("url")),
                )

            for uuid, old_target_conf in self.old_target_configs.items():
                self.assertDictEqual(self.config.get("targets", uuid), old_target_conf)
