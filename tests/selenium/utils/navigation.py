""" Code for navigation """

from utils.constants import Constants
from time import sleep
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException


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
        block_overlay_classname = "div.blockUI.blockOverlay"
        jGrowl_notification_classname = "div.jGrowl-notification.highlight.ui-corner-all.default"
        for wait_before_count in xrange(self.WAIT_TIME):
            is_overlay = self.wait_for_loading_page(block_overlay_classname)
            is_jGrowl_notification = self.wait_for_loading_page(jGrowl_notification_classname)
            if is_overlay or is_jGrowl_notification:
                print "Waiting for UI to load BEFORE clicking target element"
                sleep(2)
            else:
                link_handle = self._driver.find_element_by_id(element_id)
                link_handle.click()
                for wait_after_count in xrange(self.WAIT_TIME):
                    is_overlay = self.wait_for_loading_page(block_overlay_classname)
                    is_jGrowl_notification = self.wait_for_loading_page(jGrowl_notification_classname)
                    if is_overlay or is_jGrowl_notification:
                        print "Waiting for UI to load AFTER clicking target element"
                        sleep(2)
                        continue
                    else:
                        break
                break

    def wait_for_loading_page(self, blocking_element_class):
        try:
            blocking_div = self._driver.find_element_by_css_selector(blocking_element_class)
            try:
                if blocking_div.is_displayed():
                    return True
            except StaleElementReferenceException:
                return False
        except NoSuchElementException:
            return False
