angular.module('fixtures').run(function (fixtures) {
  'use strict';

  fixtures.registerFixture('session', {
    read_enabled: true,
    resource_uri: '/api/session/',
    user: {
      accepted_eula: false,
      alert_subscriptions: [],
      email: 'debug@debug.co.eh',
      eula_state: 'eula',
      first_name: '',
      full_name: '',
      groups: [{id: '1', name: 'superusers', resource_uri: '/api/group/1/'}],
      id: '1',
      is_superuser: true,
      last_name: '',
      new_password1: null,
      new_password2: null,
      password1: null,
      password2: null,
      resource_uri: '/api/user/1/',
      username: 'debug'
    }
  })
  .registerFixture('session', 200, {
    read_enabled: true,
    resource_uri: '/api/session/',
    user: null
  })
  .registerFixture('session', 400, {
    password: ['This field is mandatory'],
    username: ['This field is mandatory']
  })
  .registerFixture('session', {
    read_enabled: true,
    resource_uri: '/api/session/',
    user: {
      accepted_eula: false,
      alert_subscriptions: [],
      email: 'admin@debug.co.eh',
      eula_state: 'denied',
      first_name: '',
      full_name: '',
      groups: [
        {
          id: '2',
          name: 'filesystem_administrators',
          resource_uri: '/api/group/2/'
        }
      ],
      id: '2',
      is_superuser: false,
      last_name: '',
      new_password1: null,
      new_password2: null,
      password1: null,
      password2: null,
      resource_uri: '/api/user/2/',
      username: 'admin'
    }
  });
});
