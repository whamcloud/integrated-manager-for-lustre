'use strict';

var cprThenModule = require('../../lib/cpr-then').wiretree;

describe('cpr then module', function () {
  var cprThen, Promise, cpr;

  beforeEach(function () {
    cpr = {};

    Promise = {
      denodeify: jasmine.createSpy('denodeify')
        .and.returnValue(function denodeified () {})
    };

    cprThen = cprThenModule(cpr, Promise);
  });

  it('should return a function', function () {
    expect(cprThen).toEqual(jasmine.any(Function));
  });

  it('should call Promise.denodeify with cpr', function () {
    expect(Promise.denodeify).toHaveBeenCalledWith(cpr);
  });
});
