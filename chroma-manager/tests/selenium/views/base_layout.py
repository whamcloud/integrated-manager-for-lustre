class Baselayout:
    """
    Page Object for Base Layout
    """
    def __init__(self, driver):
        self.driver = driver
        self.navigation_pages = ['Dashboard', 'Configure', 'Alerts', 'Events', 'Logs']
        self.menu_element_ids = ['#dashboard-menu', '#configure-menu', '#alert-menu', '#event-menu', '#log-menu']
        self.image_element_css = ['.navbar .logo']
