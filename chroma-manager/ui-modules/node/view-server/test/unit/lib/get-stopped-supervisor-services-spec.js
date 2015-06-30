'use strict';

var proxyquire = require('proxyquire').noPreserveCache();
var λ = require('highland');

describe('get stopped supervisor services', function () {
  var xmlrpc, methodCall, getSupervisorCredentials,
    callback, getStoppedSupervisorServices;

  beforeEach(function () {
    methodCall = jasmine.createSpy('methodCall').and.callFake(function (method, args, cb) {
      callback = cb;
    });

    xmlrpc = {
      createClient: jasmine.createSpy('createClient').and.returnValue({
        methodCall: methodCall
      })
    };

    getSupervisorCredentials = jasmine.createSpy('getSupervisorCredentials').and.returnValue(λ([{
      user: null,
      pass: null
    }]));

    getStoppedSupervisorServices = proxyquire('../../../lib/get-stopped-supervisor-services', {
      xmlrpc: xmlrpc,
      './get-supervisor-credentials': getSupervisorCredentials
    });
  });

  it('should create a client', function (done) {
    getStoppedSupervisorServices()
      .apply(function () {
        expect(xmlrpc.createClient).toHaveBeenCalledOnceWith({
          host: 'localhost',
          port: 9100,
          path: '/RPC2',
          basic_auth: {
            user: null,
            pass: null
          }
        });

        done();
      });

    callback(null, []);
  });

  it('should get all process info', function (done) {
    getStoppedSupervisorServices()
      .apply(function () {
        expect(methodCall).toHaveBeenCalledOnceWith('supervisor.getAllProcessInfo', [], jasmine.any(Function));

        done();
      });

    callback(null, []);
  });

  it('should return the non-running services', function (done) {
    getStoppedSupervisorServices()
      .apply(function (x) {
        expect(x).toEqual('corosync');

        done();
      });

    callback(null, [
      {
        statename: 'RUNNING',
        name: 'primus'
      },
      {
        statename: 'STOPPED',
        name: 'corosync'
      }
    ]);
  });
});
