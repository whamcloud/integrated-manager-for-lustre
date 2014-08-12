'use strict';

var primusFactory = require('../../primus');

describe('primus', function () {
  var Primus, Emitter, server, multiplex, primusServerWrite, primus;

  beforeEach(function () {
    Primus = jasmine.createSpy('Primus').andReturn({
      use: jasmine.createSpy('primus.use')
    });

    server = {};
    multiplex = {};
    primusServerWrite = {};
    Emitter = function Emitter () {};

    primus = primusFactory(Primus, server, multiplex, primusServerWrite, Emitter);
  });

  it('should create a primus instance', function () {
    expect(Primus).toHaveBeenCalledOnceWith(server, {
      parser: 'JSON',
      transformer: jasmine.any(String)
    });
  });

  it('should use the multiplex plugin', function () {
    expect(primus.use).toHaveBeenCalledOnceWith('multiplex', multiplex);
  });

  it('should use the primusServerWrite plugin', function () {
    expect(primus.use).toHaveBeenCalledOnceWith('serverWrite', primusServerWrite);
  });

  it('should use the Emitter plugin', function () {
    expect(primus.use).toHaveBeenCalledOnceWith('emitter', Emitter);
  });
});
