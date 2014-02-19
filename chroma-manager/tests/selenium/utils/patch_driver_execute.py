#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait

from tests.selenium.utils.constants import wait_time


old_execute = WebDriver.execute


def patch_driver_execute():
    def patched_execute(self, driver_command, params=None):
        long_wait = wait_time["long"]

        if driver_command == Command.CLICK_ELEMENT:
            def find_modal_components(driver):
                driver.find_element_by_class_name("modal-backdrop")
                return driver.find_element_by_class_name("disconnect-modal")

            WebDriverWait(self, long_wait).until_not(find_modal_components,
                                                 "Disconnect modal still visible after %s seconds!" % long_wait)

        return old_execute(self, driver_command, params)

    WebDriver.execute = patched_execute
