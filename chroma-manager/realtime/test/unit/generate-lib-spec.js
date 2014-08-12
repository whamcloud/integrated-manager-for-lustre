'use strict';

var proxyquire = require('proxyquire');

describe('generate lib', function () {
  var generateLib, httpStub, serverStub, PrimusStub,
    primusStub, primusMultiplexStub, EmitterStub, primusServerWriteStub, lib;

  beforeEach(function () {
    serverStub = jasmine.createSpy('serverStub');

    httpStub = {
      createServer: jasmine.createSpy('https.createServer').andReturn(serverStub)
    };

    PrimusStub = jasmine.createSpy('Primus');

    primusStub = jasmine.createSpy('primus')
      .andReturn({
      library: function () {
        return 'foo';
      }
    });

    primusMultiplexStub = jasmine.createSpy('primusMultiplex');

    primusServerWriteStub = jasmine.createSpy('primusServerWrite');

    EmitterStub = jasmine.createSpy('Emitter');

    generateLib = proxyquire('../../generate-lib', {
      http: httpStub,
      primus: PrimusStub,
      './primus': primusStub,
      'primus-multiplex': primusMultiplexStub,
      'primus-emitter': EmitterStub,
      './primus-server-write': function primusServerWriteFactory () {
        return primusServerWriteStub;
      }
    });

    lib = generateLib();
  });

  it('should create the server', function () {
    expect(httpStub.createServer).toHaveBeenCalledOnce();
  });

  it('should create Primus with the expected params', function () {
    expect(primusStub).toHaveBeenCalledOnceWith(
      PrimusStub, serverStub, primusMultiplexStub, primusServerWriteStub, EmitterStub);
  });

  it('should return the client lib when called', function () {
    expect(lib).toEqual('foo');
  });
});
