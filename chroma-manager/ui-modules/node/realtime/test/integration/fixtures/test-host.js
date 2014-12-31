'use strict';

module.exports = function () {
  return {
    twoServers: {
      request: {
        method: 'POST',
        url: '/api/test_host/',
        data: {
          objects: [
            {
              address: 'lotus-34vm5.iml.intel.com',
              auth_type: 'existing_keys_choice'
            },
            {
              address: 'lotus-34vm6.iml.intel.com',
              auth_type: 'existing_keys_choice'
            }
          ]
        },
        headers: {}
      },
      response: {
        status: 202,
        headers: {},
        data: {
          objects: [
            {
              command: {
                cancelled: false,
                complete: false,
                created_at: '2015-01-09T14:18:57.516751+00:00',
                dismissed: false,
                errored: false,
                id: '2',
                jobs: [
                  '/api/job/2/'
                ],
                logs: '',
                message: 'Testing Connection To Host lotus-34vm5.iml.intel.com',
                resource_uri: '/api/command/2/'
              },
              error: null,
              traceback: null
            },
            {
              command: {
                cancelled: false,
                complete: false,
                created_at: '2015-01-09T14:18:57.585850+00:00',
                dismissed: false,
                errored: false,
                id: '3',
                jobs: [
                  '/api/job/3/'
                ],
                logs: '',
                message: 'Testing Connection To Host lotus-34vm6.iml.intel.com',
                resource_uri: '/api/command/3/'
              },
              error: null,
              traceback: null
            }
          ]
        }
      },
      dependencies: [],
      expires: 0
    }
  };
};
