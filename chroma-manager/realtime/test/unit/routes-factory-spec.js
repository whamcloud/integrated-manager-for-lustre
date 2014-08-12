'use strict';

var routesFactory = require('../../routes/routes-factory');

describe('routes', function () {
  var routes, wildcardRoutes;

  beforeEach(function () {
    wildcardRoutes = jasmine.createSpy('wildcardRoutes');

    routes = routesFactory(wildcardRoutes)();
  });

  it('should invoke the wildcardRoutes', function () {
    expect(wildcardRoutes).toHaveBeenCalledOnce();
  });
});
