'use strict';

module.exports = function () {
  return {
    twoServers: {
      request: {
        method: 'GET',
        url: '/api/job/?id__in=2&id__in=3&limit=0',
        data: {},
        headers: {}
      },
      response: {
        status: 200,
        headers: {},
        data: {
          meta: {
            limit: 20,
            next: null,
            offset: 0,
            previous: null,
            total_count: 2
          },
          objects: [
            {
              available_transitions: [],
              cancelled: false,
              class_name: 'TestHostConnectionJob',
              commands: [
                '/api/command/2/'
              ],
              created_at: '2015-01-09T14:18:57.519464+00:00',
              description: 'Test for host connectivity',
              errored: false,
              id: '2',
              modified_at: '2015-01-09T14:18:57.519397+00:00',
              read_locks: [],
              resource_uri: '/api/job/2/',
              state: 'complete',
              step_results: {
                '/api/step/2/': {
                  address: 'lotus-34vm5.iml.intel.com',
                  status: [
                    {
                      name: 'resolve',
                      value: true
                    },
                    {
                      name: 'ping',
                      value: true
                    },
                    {
                      name: 'auth',
                      value: true
                    },
                    {
                      name: 'hostname_valid',
                      value: true
                    },
                    {
                      name: 'fqdn_resolves',
                      value: true
                    },
                    {
                      name: 'fqdn_matches',
                      value: true
                    },
                    {
                      name: 'reverse_resolve',
                      value: true
                    },
                    {
                      name: 'reverse_ping',
                      value: true
                    },
                    {
                      name: 'yum_valid_repos',
                      value: true
                    },
                    {
                      name: 'yum_can_update',
                      value: true
                    },
                    {
                      name: 'openssl',
                      value: true
                    }
                  ],
                  valid: true
                }
              },
              steps: [
                '/api/step/2/'
              ],
              wait_for: [],
              write_locks: []
            },
            {
              available_transitions: [],
              cancelled: false,
              class_name: 'TestHostConnectionJob',
              commands: [
                '/api/command/3/'
              ],
              created_at: '2015-01-09T14:18:57.587166+00:00',
              description: 'Test for host connectivity',
              errored: false,
              id: '3',
              modified_at: '2015-01-09T14:18:57.587139+00:00',
              read_locks: [],
              resource_uri: '/api/job/3/',
              state: 'complete',
              step_results: {
                '/api/step/3/': {
                  address: 'lotus-34vm6.iml.intel.com',
                  status: [
                    {
                      name: 'resolve',
                      value: true
                    },
                    {
                      name: 'ping',
                      value: true
                    },
                    {
                      name: 'auth',
                      value: true
                    },
                    {
                      name: 'hostname_valid',
                      value: true
                    },
                    {
                      name: 'fqdn_resolves',
                      value: true
                    },
                    {
                      name: 'fqdn_matches',
                      value: true
                    },
                    {
                      name: 'reverse_resolve',
                      value: true
                    },
                    {
                      name: 'reverse_ping',
                      value: true
                    },
                    {
                      name: 'yum_valid_repos',
                      value: true
                    },
                    {
                      name: 'yum_can_update',
                      value: true
                    },
                    {
                      name: 'openssl',
                      value: true
                    }
                  ],
                  valid: true
                }
              },
              steps: [
                '/api/step/3/'
              ],
              wait_for: [],
              write_locks: []
            }
          ]
        }
      },
      dependencies: [],
      expires: 0
    }
  };
};
