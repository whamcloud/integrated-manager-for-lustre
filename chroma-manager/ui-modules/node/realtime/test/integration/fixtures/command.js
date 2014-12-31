'use strict';

module.exports = function () {
  return {
    twoServers: {
      request: {
        method: 'GET',
        url: '/api/command/?id__in=2&id__in=3&limit=0',
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
              cancelled: false,
              complete: true,
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
            {
              cancelled: false,
              complete: true,
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
            }
          ]
        }
      },
      dependencies: [],
      expires: 0
    }
  };
};
