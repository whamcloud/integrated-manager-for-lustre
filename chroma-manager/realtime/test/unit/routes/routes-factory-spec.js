'use strict';

var routesFactory = require('../../../routes/routes').wiretree;

describe('routes', function () {
  var routes, wildcardRoutes, srcmapReverseRoutes, testHostRoute;

  beforeEach(function () {
    wildcardRoutes = jasmine.createSpy('wildcardRoutes');

    srcmapReverseRoutes = jasmine.createSpy('srcmapReverseRoutes');

    testHostRoute = jasmine.createSpy('testHostRoute');

    routes = routesFactory(testHostRoute, srcmapReverseRoutes, wildcardRoutes)();
  });

  it('should invoke the wildcardRoutes', function () {
    expect(wildcardRoutes).toHaveBeenCalledOnce();
  });

  it('should invoke the srcmapReverseRoutes', function () {
    expect(srcmapReverseRoutes).toHaveBeenCalledOnce();
  });

  it('should invoke the testHostRoute', function () {
    expect(testHostRoute).toHaveBeenCalledOnce();
  });
});
