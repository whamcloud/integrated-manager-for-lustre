"""Page Object of Base Layout """


class Baselayout:
    """ Page Object for Base Layout
    """
    def __init__(self, driver):
        self.driver = driver

        # Initialise all elements on header and left panel
        self.logo_head = self.driver.find_element_by_class_name('logohead')
        self.dashboard_menu = self.driver.find_element_by_id('dashboard_menu')
        self.hydracm_menu = self.driver.find_element_by_id('hydracm_menu')
        self.alerts_menu = self.driver.find_element_by_id('alerts_menu')
        self.events_menu = self.driver.find_element_by_id('events_menu')
        self.logs_menu = self.driver.find_element_by_id('logs_menu')
        self.signbtn = self.driver.find_element_by_id('signbtn')

    #Check whether elements are present on UI

    def is_logo_head(self):
        """Returns whether if logo_head is displayed
        """
        return self.logo_head.is_displayed()

    def is_dashboard_menu(self):
        """Returns whether if dashboard_menu is displayed
        """
        return self.dashboard_menu.is_displayed()

    def is_hydracm_menu(self):
        """Returns whether if hydracm_menu is displayed
        """
        return self.hydracm_menu.is_displayed()

    def is_alerts_menu(self):
        """Returns whether if alerts_menu is displayed
        """
        return self.alerts_menu.is_displayed()

    def is_events_menu(self):
        """Returns whether if events_menu is displayed
        """
        return self.events_menu.is_displayed()

    def is_logs_menu(self):
        """Returns whether if logs_menu is displayed
        """
        return self.logs_menu.is_displayed()

    def is_signbtn(self):
        """Returns whether if signbtn is displayed
        """
        return self.signbtn.is_displayed()
