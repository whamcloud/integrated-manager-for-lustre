'use strict';

var primusFactory = require('../../primus');

describe('primus', function () {
  var Primus, server, multiplex, primus, ret;

  beforeEach(function () {
    primus = {
      use: jasmine.createSpy('primus.use')
    };

    Primus = jasmine.createSpy('Primus').andReturn(primus);

    server = multiplex = {};

    ret = primusFactory(Primus, server, multiplex);
  });

  it('should create a primus instance', function () {
    expect(Primus).toHaveBeenCalledOnceWith(server, {parser: 'JSON', transformer: jasmine.any(String)});
  });

  it('should use the multiplex plugin', function () {
    expect(primus.use).toHaveBeenCalledOnceWith('multiplex', multiplex);
  });

  it('should return the primus instance', function () {
    expect(ret).toBe(primus);
  });
});