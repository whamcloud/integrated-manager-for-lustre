'use strict';

var delThenModule = require('../../lib/del-then').wiretree;

describe('del then module', function () {
  var delThen, Promise, del;

  beforeEach(function () {
    del = function del () {};

    Promise = {
      denodeify: jasmine.createSpy('denodeify')
        .and.returnValue(function denodeified () {})
    };

    delThen = delThenModule(del, Promise);
  });

  it('should return a function', function () {
    expect(delThen).toEqual(jasmine.any(Function));
  });

  it('should call Promise.denodeify with del', function () {
    expect(Promise.denodeify).toHaveBeenCalledWith(del);
  });
});
