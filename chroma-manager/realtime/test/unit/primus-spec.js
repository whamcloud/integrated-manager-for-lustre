'use strict';

var sinon = require('sinon'),
  primusFactory = require('../../primus');

require('jasmine-sinon');

describe('primus', function () {
  var Primus, server, multiplex, primus, ret;

  beforeEach(function () {
    primus = {
      use: sinon.spy()
    };

    Primus = sinon.mock().returns(primus);

    server = multiplex = {};

    ret = primusFactory(Primus, server, multiplex);
  });

  it('should create a primus instance', function () {
    expect(Primus).toHaveBeenCalledWithExactly(server, {parser: 'JSON', transformer: sinon.match.string});
  });

  it('should use the multiplex plugin', function () {
    expect(primus.use).toHaveBeenCalledWithExactly('multiplex', multiplex);
  });

  it('should return the primus instance', function () {
    expect(ret).toBe(primus);
  });
});