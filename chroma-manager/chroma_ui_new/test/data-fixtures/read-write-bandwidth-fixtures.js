angular.module('dataFixtures').value('readWriteBandwidthDataFixtures', [
  {
    in: [
      {
        data: {
          stats_read_bytes: 106772238984.1,
          stats_write_bytes: 104418696882.20003
        },
        ts: '2013-12-11T13:15:00+00:00'
      },
      {
        data: {
          stats_read_bytes: 104677667433.3,
          stats_write_bytes: 101051194417.40001
        },
        ts: '2013-12-11T13:15:10+00:00'
      }
    ],
    out: [
      {
        key: 'read',
        values: [
          {
            y: 106772238984.1,
            x: '2013-12-11T13:15:00.000Z'
          },
          {
            y: 104677667433.3,
            x: '2013-12-11T13:15:10.000Z'
          }
        ]
      },
      {
        key: 'write',
        values: [
          {
            y: -104418696882.20003,
            x: '2013-12-11T13:15:00.000Z'
          },
          {
            y: -101051194417.40001,
            x: '2013-12-11T13:15:10.000Z'
          }
        ]
      }
    ]
  }
]);