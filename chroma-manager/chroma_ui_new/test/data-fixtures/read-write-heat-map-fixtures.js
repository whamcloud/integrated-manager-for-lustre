angular.module('dataFixtures').value('readWriteHeatMapDataFixtures', [
  {
    in: {
      OST000a: [{
        data: {
          stats_read_bytes: 7613151815.7,
          stats_write_bytes: 6442646822.9,
          stats_read_iops: 167620.4,
          stats_write_iops: 172914.1
        },
        ts: '2014-01-07T14:42:50+00:00',
        id: '1'
      }],
      OST000b: [{
        data: {
          stats_read_bytes: 7712993095.9,
          stats_write_bytes: 6062303643.6,
          stats_read_iops: 154202.4,
          stats_write_iops: 112340.1
        },
        ts: '2014-01-07T14:42:50+00:00',
        id: '2'
      }]
    },
    out: [
      {
        key : 'OST000a',
        values : [
          {
            id: '1',
            x : '2014-01-07T14:42:50.000Z',
            stats_read_bytes: 7613151815.7,
            stats_write_bytes: 6442646822.9,
            stats_read_iops: 167620.4,
            stats_write_iops: 172914.1
          }
        ]
      },
      {
        key : 'OST000b',
        values : [
          {
            id: '2',
            x : '2014-01-07T14:42:50.000Z',
            stats_read_bytes: 7712993095.9,
            stats_write_bytes: 6062303643.6,
            stats_read_iops: 154202.4,
            stats_write_iops: 112340.1
          }
        ]
      }
    ]
  }
]);
