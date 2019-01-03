from tests.integration.installation_and_upgrade.test_installation_and_upgrade import TestInstallationAndUpgrade


class TestAllEndPoints(TestInstallationAndUpgrade):
    def test_access_all_data_all_endpoints(self):
        """ Fetch all the data from all the end points """

        # Some end points just can't be fetched so we have to ignore them.
        end_point_exceptions = ["/api/help/", "/api/test_host/"]

        end_points = self.get_json_by_uri("/api/", args={"limit": 0})

        for end_point in end_points.values():
            if end_point["list_endpoint"] not in end_point_exceptions:
                import sys

                sys.stderr.write("\nReading endpoint %s\n" % end_point["list_endpoint"])
                self.get_json_by_uri(end_point["list_endpoint"], args={"limit": 0})
                sys.stderr.write("\nRead endpoint %s\n" % end_point["list_endpoint"])
