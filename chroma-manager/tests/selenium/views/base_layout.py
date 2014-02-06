class Baselayout:
    """
    Page Object for Base Layout
    """
    def __init__(self, driver):
        self.driver = driver
        self.navigation_pages = ['Dashboard', 'Configure', 'Alerts', 'Events', 'Logs']
        self.menu_element_ids = ['#dashboard_menu', '#configure_menu', '#alert_menu', '#event_menu', '#log_menu']
        self.image_element_css = ['div.navbar .logo']
        self.sidebar_id = '#sidebar'

    @property
    def sidebar_open(self):
        return self.driver.find_element_by_css_selector('#sidebar_open div.vertical')

    @property
    def sidebar_close(self):
        return self.driver.find_element_by_css_selector('#sidebar_close')
