'use strict';

var proxyquire = require('proxyquire').noPreserveCache();

describe('view router', function () {
  var getRouter, router, checkForProblems, getSession, getCache, instance;

  beforeEach(function () {
    router = {
      addStart: jasmine.createSpy('addStart').and.callFake(r)
    };

    getRouter = jasmine.createSpy('getRouter').and.callFake(r);

    checkForProblems = function checkForProblems () {};
    getSession = function getSession () {};
    getCache = function  getCache () {};

    instance = proxyquire('../../../view-server/view-router', {
      'router': getRouter,
      './middleware/check-for-problems': checkForProblems,
      './middleware/get-session': getSession,
      './middleware/get-cache': getCache
    });

    function r () {
      return router;
    }
  });

  it('should return a router', function () {
    expect(instance).toEqual(router);
  });

  it('should check for problems on start', function () {
    expect(router.addStart).toHaveBeenCalledOnceWith(checkForProblems);
  });

  it('should get the session on start', function () {
    expect(router.addStart).toHaveBeenCalledOnceWith(getSession);
  });

  it('should get the cache on start', function () {
    expect(router.addStart).toHaveBeenCalledOnceWith(getCache);
  });
});
