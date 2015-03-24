'use strict';

var indexRouteFactory = require('../../../../view-server/routes/index-route').wiretree;

describe('index route', function () {
  var indexHandlers, checkGroup, viewRouter;

  beforeEach(function () {
    indexHandlers = {
      oldHandler: jasmine.createSpy('oldHandler'),
      newHandler: jasmine.createSpy('newHandler')
    };

    checkGroup = {
      fsAdmins: jasmine.createSpy('fsAdmins'),
      fsUsers: jasmine.createSpy('fsUsers')
    };

    var pathRouter = {
      get: jasmine.createSpy('get').and.callFake(function () {
        return pathRouter;
      })
    };

    viewRouter = {
      get: jasmine.createSpy('get'),
      route: jasmine.createSpy('route').and.returnValue(pathRouter)
    };

    indexRouteFactory(viewRouter, indexHandlers, checkGroup)();
  });

  it('should have a route for hsm', function () {
    expect(viewRouter.get).toHaveBeenCalledOnceWith('/ui/configure/hsm', indexHandlers.newHandler);
  });

  it('should have a route for server', function () {
    expect(viewRouter.get).toHaveBeenCalledOnceWith('/ui/configure/server/:id*', indexHandlers.newHandler);
  });
});
