angular.module('dataFixtures').value('spaceUsageDataFixtures', [
  {
    in: [
      {
        data: {
          kbytesfree: 679928,
          kbytestotal: 2015824
        },
        ts: '2014-04-14T13:11:50+00:00'
      },
      {
        data: {
          kbytesfree: 849045,
          kbytestotal: 2015824
        },
        ts: '2014-04-14T13:12:00+00:00'
      }
    ],
    out: [
      {
        key : 'Space Used',
        values : [
          {
            x : '2014-04-14T13:11:50.000Z',
            y : 0.6627046805673511
          },
          {
            x : '2014-04-14T13:12:00.000Z',
            y : 0.5788099556310472
          }
        ]
      }
    ]
  }
]);