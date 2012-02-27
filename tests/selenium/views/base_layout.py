"""Page Object of Base Layout """


class Baselayout:
    """ Page Object for Base Layout
    """
    def __init__(self, driver):
        self.driver = driver

        # Initialise all elements on header and left panel
        self.logo_head = self.driver.find_element_by_class_name('logohead')
        self.dashboard_menu = self.driver.find_element_by_id('dashboard_menu')
        self.configure_menu = self.driver.find_element_by_id('configure_menu')
        self.alerts_menu = self.driver.find_element_by_id('alert_menu')
        self.events_menu = self.driver.find_element_by_id('event_menu')
        self.logs_menu = self.driver.find_element_by_id('log_menu')
        self.sidebar_open = self.driver.find_element_by_css_selector("div.vertical")
        self.sidebar = self.driver.find_element_by_id('sidebar')

    #Check whether elements are present on UI

    def logo_head_displayed(self):
        """Returns whether if logo_head is displayed
        """
        return self.logo_head.is_displayed()

    def dashboard_menu_displayed(self):
        """Returns whether if dashboard_menu is displayed
        """
        return self.dashboard_menu.is_displayed()

    def configure_menu_displayed(self):
        """Returns whether if configure_menu is displayed
        """
        return self.configure_menu.is_displayed()

    def alerts_menu_displayed(self):
        """Returns whether if alerts_menu is displayed
        """
        return self.alerts_menu.is_displayed()

    def events_menu_displayed(self):
        """Returns whether if events_menu is displayed
        """
        return self.events_menu.is_displayed()

    def logs_menu_displayed(self):
        """Returns whether if logs_menu is displayed
        """
        return self.logs_menu.is_displayed()

    def open_sidebar(self):
        """Returns whether if signbtn is displayed
        """
        return self.sidebar_open.click()

    def sidebar_displayed(self):
        """Returns whether if signbtn is displayed
        """
        return self.sidebar.is_displayed()
