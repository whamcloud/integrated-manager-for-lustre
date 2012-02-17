""" Test Data """
import json


class Testdata:
    """Class contains all links to navigate in the UI
    """

    def __init__(self):
        """ Data used used by the tests should be mentioned here
        """

        self.json_data = open('../sample_data/example.json')
        self.test_data = json.load(self.json_data)

    def get_test_data_for_server_configuration(self):
        host_list = self.test_data["hosts"]
        return host_list

    def get_test_data_for_mgt_configuration(self):
        mgs_list = self.test_data["mgss"]
        return mgs_list

    def get_test_data_for_filesystem_configuration(self):
        fs_list = self.test_data["filesystems"]
        return fs_list
