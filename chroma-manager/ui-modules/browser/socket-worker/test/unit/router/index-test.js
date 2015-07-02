'use strict';

var proxyquire = require('proxyquire').noPreserveCache();

describe('router', function () {
  var getRouter, router, r;

  beforeEach(function () {
    router = {
      router: true
    };

    getRouter = jasmine.createSpy('router')
      .and.returnValue(router);

    r = proxyquire('../../../router/index', {
      'router': getRouter
    });
  });

  it('should instantiate the router', function () {
    expect(getRouter).toHaveBeenCalledOnce();
  });

  it('should export the router', function () {
    expect(r).toBe(router);
  });
});
