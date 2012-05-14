class Breadcrumb:
    """
    Page Object for Breadcrumb
    """
    def __init__(self, driver):
        self.driver = driver

        # Initialise elements in breadcrumb on dashboard page
        self.selectView = '#selectView'
        self.intervalSelect = '#intervalSelect'
        self.unitSelect = '#unitSelect'
        self.fsSelect = '#fsSelect'
        self.serverSelect = '#serverSelect'
        self.ostSelect = '#ostSelect'

    def get_units_list(self):
        """Returns unit values list"""
        unit_select = self.driver.find_element_by_css_selector(self.unitSelect)
        units_list_options = unit_select.find_elements_by_tag_name('option')
        # Remove the default option "Select Server" from original list
        filtered_list_options = units_list_options[1:units_list_options.__len__()]
        filtered_unit_list = []
        for count in range(len(filtered_list_options)):
            filtered_unit_list.append(int(filtered_list_options.__getitem__(count).text))
        filtered_unit_list.sort()
        return filtered_unit_list

    def get_expected_unit_list(self, time_interval):
        """Returns expected unit values list"""

        expected_unit_list = []
        if time_interval == 'Minutes':
            for count in range(60):
                expected_unit_list.append(count + 1)
        elif time_interval == 'Hour':
            for count in range(23):
                expected_unit_list.append(count + 1)
        elif time_interval == 'Day':
            for count in range(31):
                expected_unit_list.append(count + 1)
        elif time_interval == 'Week':
            for count in range(4):
                expected_unit_list.append(count + 1)

        return expected_unit_list

    def get_filesystem_list(self):
        """Returns file system list"""
        fs_select = self.driver.find_element_by_css_selector(self.fsSelect)
        filesystem_list_options = fs_select.find_elements_by_tag_name('option')
        if filesystem_list_options.__len__() == 0:
            raise RuntimeError("No file system list on dashboard breadcrumb")
        else:
            # Remove the default option "Select FileSystem" from original list
            filtered_list_options = filesystem_list_options[1:filesystem_list_options.__len__()]
            filtered_filesystem_list = []
            for count in range(len(filtered_list_options)):
                filtered_filesystem_list.append(filtered_list_options.__getitem__(count).text)
            filtered_filesystem_list.sort()
            return filtered_filesystem_list

    def get_server_list(self):
        """Returns server list"""
        server_select = self.driver.find_element_by_css_selector(self.serverSelect)
        server_list_options = server_select.find_elements_by_tag_name('option')
        if server_list_options.__len__() == 1:
            raise RuntimeError("No server list on dashboard breadcrumb")
        else:
            # Remove the default option "Select Server" from original list
            filtered_list_options = server_list_options[1:server_list_options.__len__()]
            filtered_server_list = []
            for count in range(len(filtered_list_options)):
                filtered_server_list.append(filtered_list_options.__getitem__(count).text)
            filtered_server_list.sort()
            return filtered_server_list

    def get_target_list(self):
        """Returns target list"""
        target_select = self.driver.find_element_by_css_selector(self.ostSelect)
        target_list_options = target_select.find_elements_by_tag_name('option')
        if target_list_options.__len__() == 1:
            raise RuntimeError("No target list on dashboard breadcrumb")
        else:
            # Remove the default option "Select Target" from original list
            filtered_list_options = target_list_options[1:target_list_options.__len__()]
            filtered_target_list = []
            for count in range(len(filtered_list_options)):
                filtered_target_list.append(filtered_list_options.__getitem__(count).text)
            filtered_target_list.sort()
            return filtered_target_list
