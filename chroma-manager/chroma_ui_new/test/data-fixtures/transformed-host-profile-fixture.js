angular.module('dataFixtures').value('transformedHostProfileFixture', [
  {
    name: 'base_managed',
    uiName: 'Managed Storage Server',
    invalid: true,
    hosts: [
      {
        address: 'lotus-34vm5.iml.intel.com',
        invalid: true,
        problems: [
          {
            description: 'ZFS is installed but is unsupported by the Managed Storage Server profile',
            error: 'Result unavailable while host agent starts',
            pass: false,
            test: 'zfs_installed == False'
          }
        ],
        uiName: 'Managed Storage Server'
      },
      {
        address: 'lotus-34vm6.iml.intel.com',
        invalid: true,
        problems: [
          {
            description: 'ZFS is installed but is unsupported by the Managed Storage Server profile',
            error: 'Result unavailable while host agent starts',
            pass: false,
            test: 'zfs_installed == False'
          }
        ],
        uiName: 'Managed Storage Server'
      }
    ]
  },
  {
    name: 'base_monitored',
    uiName: 'Monitored Storage Server',
    invalid: false,
    hosts: [
      {
        address: 'lotus-34vm5.iml.intel.com',
        invalid: false,
        problems: [],
        uiName: 'Monitored Storage Server'
      },
      {
        address: 'lotus-34vm6.iml.intel.com',
        invalid: false,
        problems: [],
        uiName: 'Monitored Storage Server'
      }
    ]
  },
  {
    name: 'posix_copytool_worker',
    uiName: 'POSIX HSM Agent Node',
    invalid: false,
    hosts: [
      {
        address: 'lotus-34vm5.iml.intel.com',
        invalid: false,
        problems: [],
        uiName: 'POSIX HSM Agent Node'
      },
      {
        address: 'lotus-34vm6.iml.intel.com',
        invalid: false,
        problems: [],
        uiName: 'POSIX HSM Agent Node'
      }
    ]
  },
  {
    name: 'robinhood_server',
    uiName: 'Robinhood Policy Engine Server',
    invalid: false,
    hosts: [
      {
        address: 'lotus-34vm5.iml.intel.com',
        invalid: false,
        problems: [],
        uiName: 'Robinhood Policy Engine Server'
      },
      {
        address: 'lotus-34vm6.iml.intel.com',
        invalid: false,
        problems: [],
        uiName: 'Robinhood Policy Engine Server'
      }
    ]
  }
]);
