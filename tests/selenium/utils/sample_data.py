from testconfig import config


class Testdata:
    """
    This class reads and returns data from config file that is used by the test cases
    """

    def get_test_data_for_server_configuration(self):
        # read and return host related data from config file
        host_list = config["hosts"]
        return host_list

    def get_test_data_for_mgt_configuration(self):
        # read and return mgs related data from config file
        mgs_list = config["mgss"]
        return mgs_list

    def get_test_data_for_filesystem_configuration(self):
        # read and return file system related data from config file
        fs_list = config["filesystems"]
        return fs_list
