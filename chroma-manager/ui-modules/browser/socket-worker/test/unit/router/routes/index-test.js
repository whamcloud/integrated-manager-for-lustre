'use strict';

var proxyquire = require('proxyquire').noPreserveCache();

describe('router', function () {
  var index, wildcard;

  beforeEach(function () {
    wildcard = jasmine.createSpy('wildcard');

    index = proxyquire('../../../../router/routes/index', {
      './wildcard': wildcard
    });
  });

  it('should have a wildcard route', function () {
    expect(index.wildcard).toEqual(wildcard);
  });
});
