angular.module('dataFixtures').value('memoryUsageDataFixtures', [
  {
    in: [
      {
        data: {
          mem_MemFree: 23956,
          mem_MemTotal: 509856,
          mem_SwapFree: 1048568,
          mem_SwapTotal: 1048568
        },
        ts: '2014-04-14T13:23:50+00:00'
      },
      {
        data: {
          mem_MemFree: 19214,
          mem_MemTotal: 509856,
          mem_SwapFree: 1048568,
          mem_SwapTotal: 1048568
        },
        ts: '2014-04-14T13:24:00+00:00'
      }
    ],
    out: [
      {
        key: 'Total memory',
        values: [
          { x: '2014-04-14T13:23:50.000Z', y: 522092544 },
          { x: '2014-04-14T13:24:00.000Z', y: 522092544 }
        ]
      },
      {
        key: 'Used memory',
        values: [
          { x: '2014-04-14T13:23:50.000Z', y: 497561600 },
          { x: '2014-04-14T13:24:00.000Z', y: 502417408 }
        ]
      },
      {
        key: 'Total swap',
        values: [
          { x: '2014-04-14T13:23:50.000Z', y: 1073733632 },
          { x: '2014-04-14T13:24:00.000Z', y: 1073733632 }
        ]
      },
      {
        key: 'Used swap',
        values: [
          { x: '2014-04-14T13:23:50.000Z', y: 0 },
          { x: '2014-04-14T13:24:00.000Z', y: 0 }
        ]
      }
    ]
  }
]);