'use strict';

var λ = require('highland');
var loginRouteFactory = require('../../../../view-server/routes/login-route').wiretree;

describe('login route', function () {
  var viewRouter, templates, req, res, next, push,
    cache, requestStream, pathRouter, renderRequestError, renderRequestErrorInner;

  beforeEach(function () {
    req = {};

    res = {
      redirect: jasmine.createSpy('redirect'),
      clientRes: {
        setHeader: jasmine.createSpy('setHeader'),
        end: jasmine.createSpy('end')
      }
    };

    next = jasmine.createSpy('next');

    cache = { session: {} };

    templates = {
      'new/index.html': jasmine.createSpy('indexTemplate')
        .and.returnValue('foo')
    };

    pathRouter = {
      get:  jasmine.createSpy('get').and.callFake(function () {
        return pathRouter;
      })
    };

    viewRouter = {
      route: jasmine.createSpy('route').and.returnValue(pathRouter)
    };

    requestStream = jasmine.createSpy('requestStream').and.returnValue(λ(function (_push_) {
      push = _push_;
    }));

    renderRequestErrorInner = jasmine.createSpy('renderRequestErrorInner');

    renderRequestError = jasmine.createSpy('renderRequestError')
      .and.returnValue(renderRequestErrorInner);

    loginRouteFactory(viewRouter, templates, requestStream, renderRequestError)();
  });

  it('should register a path for the login route', function () {
    expect(viewRouter.route).toHaveBeenCalledOnceWith('/ui/login');
  });

  describe('eula checking', function () {
    var handler, data;

    beforeEach(function () {
      data = {
        cacheCookie: 'foo',
        cache: {
          session: {}
        }
      };

      handler = pathRouter.get.calls.first().args[0];
    });

    it('should go to next if user is undefined', function () {
      handler(req, res, data, next);

      expect(next).toHaveBeenCalledOnceWith(req, res, data.cache);
    });

    it('should redirect if the user exists and accepted eula', function () {
      data.cache.session.user = {
        eula_state: 'pass'
      };

      handler(req, res, data, next);

      expect(res.redirect).toHaveBeenCalledOnceWith('/ui/');
    });

    describe('deleting session', function () {
      beforeEach(function () {
        data.cache.session.user = {
          eula_state: 'eula'
        };

        handler(req, res, data, next);
      });

      it('should send a delete request', function () {
        expect(requestStream).toHaveBeenCalledOnceWith('/session', {
          method: 'delete',
          headers: { cookie : 'foo' }
        });
      });

      it('should call next', function () {
        push(null, []);
        push(null, nil);

        expect(next).toHaveBeenCalledOnceWith(req, res, data.cache);
      });

      it('should render errors', function () {
        push(new Error('boom!'));
        push(null, nil);

        expect(renderRequestErrorInner).toHaveBeenCalledOnceWith(new Error('boom!'), jasmine.any(Function));
      });
    });

  });

  describe('render login', function () {
    beforeEach(function () {
      var handler = pathRouter.get.calls.mostRecent().args[0];
      handler(req, res, {}, next);
    });

    it('should set the header', function () {
      expect(res.clientRes.setHeader).toHaveBeenCalledOnceWith('Content-Type', 'text/html; charset=utf-8');
    });

    it('should set the statusCode', function () {
      expect(res.clientRes.statusCode).toBe(200);
    });

    it('should render the body', function () {
      expect(res.clientRes.end).toHaveBeenCalledOnceWith('foo');
    });

    it('should render the template', function () {
      expect(templates['new/index.html']).toHaveBeenCalledOnceWith({
        title: 'Login',
        cache: {}
      });
    });

    it('should call next', function () {
      expect(next).toHaveBeenCalledOnceWith(req, res);
    });
  });
});
