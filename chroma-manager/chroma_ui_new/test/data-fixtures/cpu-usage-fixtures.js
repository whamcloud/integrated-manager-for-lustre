angular.module('dataFixtures').value('cpuUsageDataFixtures', [
  {
    in: [
      {
        data: {
          cpu_iowait: 0,
          cpu_system: 0,
          cpu_total: 12.4,
          cpu_user: 5.9
        },
        ts: '2014-04-11T01:18:40+00:00'
      },
      {
        data: {
          cpu_iowait: 0,
          cpu_system: 0,
          cpu_total: 12.8,
          cpu_user: 5
        },
        ts: '2014-04-11T01:18:50+00:00'
      }
    ],
    out: [
      {
        key: 'user',
        values: [
          { x: '2014-04-11T01:18:40.000Z', y: 0.48080645161290325 },
          { x: '2014-04-11T01:18:50.000Z', y: 0.39562499999999995 }
        ]
      },
      {
        key: 'system',
        values: [
          { x: '2014-04-11T01:18:40.000Z', y: 0.005 },
          { x: '2014-04-11T01:18:50.000Z', y: 0.005 }
        ]
      },
      {
        key: 'iowait',
        values: [
          { x: '2014-04-11T01:18:40.000Z', y: 0.005 },
          { x: '2014-04-11T01:18:50.000Z', y: 0.005 }
        ]
      }
    ]
  }
]);