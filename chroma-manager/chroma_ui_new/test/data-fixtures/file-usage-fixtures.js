angular.module('dataFixtures').value('fileUsageDataFixtures', [
  {
    in: [
      {
        data: {
          filesfree: 176109,
          filestotal: 512000
        },
        ts: '2014-04-14T13:39:40+00:00'
      },
      {
        data: {
          filesfree: 140602,
          filestotal: 512000
        },
        ts: '2014-04-14T13:40:00+00:00'
      }
    ],
    out: [
      {
        key: 'Files Used',
        values: [
          { x: '2014-04-14T13:39:40.000Z', y: 0.656037109375 },
          { x: '2014-04-14T13:40:00.000Z', y: 0.72538671875 }
        ]
      }
    ]
  }
]);