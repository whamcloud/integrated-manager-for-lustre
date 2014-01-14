'use strict';

var sinon = require('sinon'),
  proxyquire = require('proxyquire');

require('jasmine-sinon');

describe('generate lib', function () {
  var generateLib, httpStub, serverStub, PrimusStub,
    primusStub, primusMultiplexStub, lib;

  beforeEach(function () {
    serverStub = sinon.spy();

    httpStub = {
      createServer: sinon.mock().returns(serverStub)
    };

    PrimusStub = sinon.mock();

    primusStub = sinon.mock().returns({
      library: function () {
        return 'foo';
      }
    });

    primusMultiplexStub = sinon.spy();

    generateLib = proxyquire('../../generate-lib', {
      http: httpStub,
      primus: PrimusStub,
      './primus': primusStub,
      'primus-multiplex': primusMultiplexStub
    });

    lib = generateLib();
  });

  it('should create the server', function () {
    expect(httpStub.createServer).toHaveBeenCalledOnce();
  });

  it('should create Primus with the expected params', function () {
    expect(primusStub).toHaveBeenCalledWith(PrimusStub, serverStub, primusMultiplexStub);
  });

  it('should return the client lib when called', function () {
    expect(lib).toEqual('foo');
  });
});