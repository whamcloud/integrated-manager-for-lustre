#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


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
        # read and return mgt related data from config file
        mgt_list = config["mgt"]
        return mgt_list

    def get_test_data_for_filesystem_configuration(self):
        # read and return file system related data from config file
        fs_list = config["filesystems"]
        return fs_list

    def get_test_data_for_editing_filesystem(self):
        # read and return data from config file for editing file system
        fs_list = config["edit_filesystem"]
        return fs_list

    def get_test_data_for_user(self):
        # read and return data from config file for adding user
        user_data = config["user"]
        return user_data
