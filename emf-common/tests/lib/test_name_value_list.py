import json
import unittest

from emf_common.lib.name_value_list import NameValueList


class TestNameValueList(unittest.TestCase):
    def setUp(self):
        self.raw_values = [
            {"resolve": False},
            {"ping": True},
            {"auth": False},
            {"hostname_valid": False},
            {"fqdn_resolves": False},
            {"fqdn_matches": False},
            {"reverse_resolve": False},
            {"reverse_ping": False},
            {"yum_valid_repos": False},
            {"yum_can_update": False},
            {"openssl": False},
        ]

        self.values = NameValueList(self.raw_values)

    def test_creation_correction(self):
        for value, raw_value in zip(self.values, self.raw_values):
            self.assertEqual(value.name, raw_value.keys()[0])
            self.assertEqual(value.value, raw_value.values()[0])

    def test_name_value_create(self):
        self.values["execute"] = True
        self.assertEqual(self.values["execute"], True)
        pass

    def test_update(self):
        self.values["resolve"] = True
        self.assertEqual(self.values["resolve"], True)

    def test_type_change(self):
        self.values["reverse_resolve"] = "string"
        self.assertEqual(self.values["reverse_resolve"], "string")

    def test_index_constant(self):
        self.values["reverse_resolve"] = True
        self.assertEqual(self.values.keys().index("reverse_resolve"), 6)

    def test_collection_via_json(self):
        json_string = json.dumps(self.values.collection())
        loaded_values = NameValueList(json.loads(json_string))
        self.assertEqual(self.values, loaded_values)

    def test_collection_len(self):
        self.assertEqual(len(self.values), len(self.values.collection()))

    def test_collection_values(self):
        for entry in self.values.collection():
            self.assertEqual(entry["value"], self.values[entry["name"]])
