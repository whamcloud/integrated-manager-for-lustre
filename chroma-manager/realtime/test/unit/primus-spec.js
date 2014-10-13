'use strict';

var primusFactory = require('../../primus');

describe('primus', function () {
  var Primus, Emitter, conf, multiplex, primusServerWrite, primus;

  beforeEach(function () {
    Primus = {
      createServer: jasmine.createSpy('createServer').andReturn({
        use: jasmine.createSpy('primus.use')
      })
    };

    conf = {
      primusPort: 8888
    };

    multiplex = {};
    primusServerWrite = {};
    Emitter = function Emitter () {};

    primus = primusFactory(Primus, conf, multiplex, primusServerWrite, Emitter);
  });

  it('should create a server', function () {
    expect(Primus.createServer).toHaveBeenCalledOnceWith({
      parser: 'JSON',
      transformer: 'socket.io',
      port: 8888,
      iknowhttpsisbetter: true
    });
  });

  it('should return a primus instance', function () {
    expect(primus).toEqual(Primus.createServer.plan());
  });

  it('should use the primusServerWrite plugin', function () {
    expect(primus.use).toHaveBeenCalledOnceWith('serverWrite', primusServerWrite);
  });

  it('should use the multiplex plugin', function () {
    expect(primus.use).toHaveBeenCalledOnceWith('multiplex', multiplex);
  });

  it('should use the Emitter plugin', function () {
    expect(primus.use).toHaveBeenCalledOnceWith('emitter', Emitter);
  });
});
