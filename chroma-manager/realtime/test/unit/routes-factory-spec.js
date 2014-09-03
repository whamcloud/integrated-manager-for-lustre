'use strict';

var routesFactory = require('../../routes/routes-factory');

describe('routes', function () {
  var routes, wildcardRoutes, srcmapReverseRoutes;

  beforeEach(function () {
    wildcardRoutes = jasmine.createSpy('wildcardRoutes');

    srcmapReverseRoutes = jasmine.createSpy('srcmapReverseRoutes');

    routes = routesFactory(wildcardRoutes, srcmapReverseRoutes)();
  });

  it('should invoke the wildcardRoutes', function () {
    expect(wildcardRoutes).toHaveBeenCalledOnce();
  });

  it('should invoke the srcmapReverseRoutes', function () {
    expect(srcmapReverseRoutes).toHaveBeenCalledOnce();
  });
});
