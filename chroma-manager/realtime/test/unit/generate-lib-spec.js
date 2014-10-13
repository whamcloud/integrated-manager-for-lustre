'use strict';

var proxyquire = require('proxyquire');

describe('generate lib', function () {
  var generateLib, PrimusStub, primusStub, primusMultiplexStub,
    EmitterStub, primusServerWriteStub, lib;

  beforeEach(function () {
    PrimusStub = jasmine.createSpy('Primus');

    primusStub = jasmine.createSpy('primus')
      .andReturn({
        library: function library () {
          return 'foo';
        },
        end: jasmine.createSpy('end')
      });

    primusMultiplexStub = jasmine.createSpy('primusMultiplex');

    primusServerWriteStub = jasmine.createSpy('primusServerWrite');

    EmitterStub = jasmine.createSpy('Emitter');

    generateLib = proxyquire('../../generate-lib', {
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

  it('should create Primus with the expected params', function () {
    expect(primusStub).toHaveBeenCalledOnceWith(
      PrimusStub, { primusPort: 8889 }, primusMultiplexStub, primusServerWriteStub, EmitterStub);
  });

  it('should return the client lib when called', function () {
    expect(lib).toEqual('foo');
  });

  it('should end the instance', function () {
    expect(primusStub.plan().end).toHaveBeenCalledOnce();
  });
});
