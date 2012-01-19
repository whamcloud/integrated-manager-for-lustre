""" Test Volumes """

from utils.navigation import Navigation
from views.volumes import Volumes
from base import SeleniumBaseTestCase
from time import sleep


class Volumesdata(SeleniumBaseTestCase):

    def test_volume_config_error_data(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation._links['Configure'])

        page_navigation.click(page_navigation._links['Volumes'])
        sleep(2)

        # Calling volumes
        volumes_page = Volumes(self.driver)

        # Verifying the volume configuration error dialog being displayed
        self.assertTrue(volumes_page.get_volume_config_error_message())

    def test_change_volume_config(self):

        # Calling navigation
        page_navigation = Navigation(self.driver)
        page_navigation.click(page_navigation._links['Configure'])

        page_navigation.click(page_navigation._links['Volumes'])
        sleep(2)

        # Calling volumes
        volumes_page = Volumes(self.driver)

        # Verifying that volume configuration setting is successful
        self.assertEqual(volumes_page.get_volume_change_message(), 'Update Successful')

import unittest
if __name__ == '__main__':
    unittest.main()
