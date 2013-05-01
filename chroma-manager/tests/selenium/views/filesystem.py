from tests.selenium.base_view import  DatatableView
from tests.selenium.utils.element import find_visible_element_by_css_selector


class Filesystem(DatatableView):
    """
    Page Object for file system operations
    """
    def __init__(self, driver):
        super(Filesystem, self).__init__(driver)

        self.filesystem_name_td = 0
        self.datatable_id = 'fs_list'

    @property
    def visible(self):
        return find_visible_element_by_css_selector(self.driver, 'div#filesystem-tab-list')

    def locate_filesystem(self, filesystem_name):
        filesystem_list = self.driver.find_elements_by_xpath("id('" + self.datatable_id + "')/tbody/tr")
        for tr in filesystem_list:
            tds = tr.find_elements_by_tag_name("td")
            if tds[self.filesystem_name_td].text == filesystem_name:
                return tr

        raise RuntimeError("File system: " + filesystem_name + " not found in file system list")

    def transition(self, filesystem_name, transition_name):
        """Perform given transition on target filesystem"""
        target_filesystem_row = self.locate_filesystem(filesystem_name)
        self.click_command_button(target_filesystem_row, transition_name)

    def edit(self, fs_name):
        """Click filesystem name to be edited"""
        target_filesystem_row = self.locate_filesystem(fs_name)
        target_filesystem_row.find_element_by_xpath("td[1]/a").click()
        self.quiesce()

    def get_filesystem_list(self):
        """Returns file system name list"""
        fs_list = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr/td[1]/a")
        filtered_filesystem_list = []

        # Get actual display text from list of webelement objects, append the names to a new list and sort the new list
        for count in range(len(fs_list)):
            filtered_filesystem_list.append(fs_list.__getitem__(count).text)
        filtered_filesystem_list.sort()
        return filtered_filesystem_list
