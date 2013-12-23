angular.module('dataFixtures').value('readWriteHeatMapDataFixtures', [
  {
    in: {
      OST000a: [{
        data: {
          stats_read_bytes: 7613151815.7,
          stats_write_bytes: 6442646822.9
        },
        ts: '2014-01-07T14:42:50+00:00'
      }],
      OST000b: [{
        data: {
          stats_read_bytes: 7712993095.9,
          stats_write_bytes: 6062303643.6
        },
        ts: '2014-01-07T14:42:50+00:00'
      }]
    },
    out: [
      {
        key : 'OST000a',
        values : [
          {
            x : '2014-01-07T14:42:50.000Z',
            stats_read_bytes: 7613151815.7,
            stats_write_bytes: 6442646822.9
          }
        ]
      },
      {
        key : 'OST000b',
        values : [
          {
            x : '2014-01-07T14:42:50.000Z',
            stats_read_bytes: 7712993095.9,
            stats_write_bytes: 6062303643.6
          }
        ]
      }
    ]
  }
]);