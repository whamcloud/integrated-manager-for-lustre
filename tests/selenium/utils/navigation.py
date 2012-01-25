""" Code for navigation """


class Navigation:
    """Class contains all links to navigate in the UI
    """

    def __init__(self, driver):
        """ Here we initiate the main header navigation links
            @param: driver : Instance of the webdriver
        """
        self._driver = driver

        self._links = {
            # Link for Dashboard
            'Dashboard': 'dashboard_menu',
            # Links for Configuration
            'Configure': 'hydracm_menu',
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

    def click(self, link_name):
        """ A generic function to click a link from the main navigation bar
        @param: link_name : Specify the link as seen on the UI
        """
        link_handle = self._driver.find_element_by_id(link_name)
        link_handle.click()
