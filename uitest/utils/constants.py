"""This function will act as settings file
"""


class Constants:
    """ An object that will have constants that will be used for the tests
    """

    def __init__(self):
        # Wait times
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
