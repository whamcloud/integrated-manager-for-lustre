angular.module('dataFixtures').value('hsmCdtDataFixtures', [
  {
    in: [
      {
        'data': {
          'hsm_actions_waiting': 0,
          'hsm_actions_running': 0,
          'hsm_agents_idle': 0
        },
        'ts': '2013-11-18T20:59:30+00:00'
      },
      {
        'data': {
          'hsm_actions_waiting': 1024,
          'hsm_actions_running': 42,
          'hsm_agents_idle': 13
        },
        'ts': '2013-11-18T20:59:40+00:00'
      },
      {
        'data': {
          'hsm_actions_running': 2.6000000000000001,
          'hsm_actions_waiting': 18.800000000000001,
          'hsm_agents_idle': 0.10000000000000001
        },
        'ts': '2013-11-18T20:59:50+00:00'
      }
    ],
    out: [
      {
        'key': 'waiting requests',
        'values': [
          {
            y: 0,
            x: '2013-11-18T20:59:30.000Z'
          },
          {
            y: 1024,
            x: '2013-11-18T20:59:40.000Z'
          },
          {
            y: 19,
            x: '2013-11-18T20:59:50.000Z'
          }
        ]
      },
      {
        'key': 'running actions',
        'values': [
          {
            y: 0,
            x: '2013-11-18T20:59:30.000Z'
          },
          {
            y: 42,
            x: '2013-11-18T20:59:40.000Z'
          },
          {
            y: 3,
            x: '2013-11-18T20:59:50.000Z'
          }
        ]
      },
      {
        'key': 'idle workers',
        'values': [
          {
            y: 0,
            x: '2013-11-18T20:59:30.000Z'
          },
          {
            y: 13,
            x: '2013-11-18T20:59:40.000Z'
          },
          {
            y: 0,
            x: '2013-11-18T20:59:50.000Z'
          }
        ]
      }
    ]
  }
]);
