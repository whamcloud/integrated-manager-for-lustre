"""This function will act as settings file
"""


class Constants:
    """ An object that will have constants that will be used for the tests
    """
    def __init__(self):
        # Wait times
        self.static_text = {
                'no_data_for_datable': 'No data available in table',
                'warning': 'WARNING'
        }

        self.wait_time = {
            'long': 60,
            'standard': 30,
            'medium': 15,
            'short': 5,
        }

    def get_wait_time(self, duration):
        """ Returns the wait time
        """
        return self.wait_time[duration]

    def get_static_text(self, text):
        """ Returns the static text
        """
        return self.static_text[text]
