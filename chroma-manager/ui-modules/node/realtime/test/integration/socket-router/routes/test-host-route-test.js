'use strict';

var utils = require('../../utils');
var fixtures = require('../../fixtures');
var start = require('../../../../index');
var waitForRequests = require('../../../../request/request-agent').waitForRequests;

describe('test host route', function () {
  var socket, shutdown, stubDaddy,
    testHostFixtures, commandFixtures, jobFixtures;

  beforeEach(function () {
    testHostFixtures = fixtures.testHost();
    commandFixtures = fixtures.command();
    jobFixtures = fixtures.job();
  });

  beforeEach(function (done) {
    stubDaddy = utils.getStubDaddy();

    stubDaddy.webService
      .startService()
      .done(done, done.fail);
  });

  beforeEach(function () {
    shutdown = start();
    socket = utils.getSocket();
  });

  afterEach(function (done) {
    stubDaddy.webService
      .stopService()
      .done(done, done.fail);
  });

  afterEach(function () {
    var result = stubDaddy.inlineService
      .mockState();

    if (result.status !== 200)
      throw new Error(result.data);
  });

  afterEach(function () {
    shutdown();
  });

  afterEach(waitForRequests);

  afterEach(function (done) {
    socket.on('disconnect', done);
    socket.close();
  });

  describe('test two servers', function () {
    beforeEach(function () {
      stubDaddy.inlineService
        .mock(testHostFixtures.twoServers);

      stubDaddy.inlineService
        .mock(commandFixtures.twoServers);

      stubDaddy.inlineService
        .mock(jobFixtures.twoServers);
    });

    it('should return the status', function (done) {
      socket.emit('message1', {
        path: '/test_host',
        options: {
          method: 'post',
          json: {
            objects: [
              {
                address: 'lotus-34vm5.iml.intel.com',
                auth_type: 'existing_keys_choice'
              },
              {
                address: 'lotus-34vm6.iml.intel.com',
                auth_type: 'existing_keys_choice'
              }
            ]
          }
        }
      });

      socket.once('message1', function (data) {
        expect(data).toEqual([
          {
            address: 'lotus-34vm5.iml.intel.com',
            status: [
              { name: 'resolve', value: true },
              { name: 'ping', value: true },
              { name: 'auth', value: true },
              { name: 'hostname_valid', value: true },
              { name: 'fqdn_resolves', value: true },
              { name: 'fqdn_matches', value: true },
              { name: 'reverse_resolve', value: true },
              { name: 'reverse_ping', value: true },
              { name: 'yum_valid_repos', value: true },
              { name: 'yum_can_update', value: true },
              { name: 'openssl', value: true }
            ],
            valid: true
          },
          {
            address: 'lotus-34vm6.iml.intel.com',
            status: [
              { name: 'resolve', value: true },
              { name: 'ping', value: true },
              { name: 'auth', value: true },
              { name: 'hostname_valid', value: true },
              { name: 'fqdn_resolves', value: true },
              { name: 'fqdn_matches', value: true },
              { name: 'reverse_resolve', value: true },
              { name: 'reverse_ping', value: true },
              { name: 'yum_valid_repos', value: true },
              { name: 'yum_can_update', value: true },
              { name: 'openssl', value: true }
            ],
            valid: true
          }]);
        done();
      });
    });
  });
});
