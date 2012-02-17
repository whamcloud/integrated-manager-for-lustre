""" Code for navigation """
from utils.constants import Constants


class Navigation:
    """Class contains all links to navigate in the UI
    """
    def __init__(self, driver):
        """ Here we initiate the main header navigation links
            @param: driver : Instance of the webdriver
        """
        self._driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time['standard']
        self.links = {
            # Link for Dashboard
            'Dashboard': 'dashboard_menu',
            # Links for Configuration
            'Configure': 'configure_menu',
            # Links under configuration
            'Filesystems': 'filesystem_tab',
            'MGTs': 'mgt_tab',
            'Volumes': 'volume_tab',
            'Servers': 'server_tab',
            'Storage': 'storage_tab',
            'Create_new_filesystem': 'create_new_fs',
            # Link for Alerts
            'Alerts': 'alerts_menu',
            # Links for Events
            'Events': 'events_menu',
            # Link for Logs
            'Logs': 'logs_menu',
            # Links under Notifications
            'Notifications': 'signbtn',
            'Notify_alerts': 'alertAnchor',
            'Notify_events': 'eventsAnchor',
            'Notify_jobs': 'jobsAnchor',
        }

    def click(self, element_id):
        """ A generic function to click a link from the main navigation bar
        @param: element_id : Specify the ID of the element to be clicked as seen on the UI
        """
        from base import wait_for_element
        link_handle = self._driver.find_element_by_id(element_id)
        link_handle.click()
        self._driver.execute_script('Api.testMode(true);')
        wait_for_element(self._driver, '#user_info #authenticated', 10)
