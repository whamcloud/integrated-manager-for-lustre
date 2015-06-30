'use strict';

var proxyquire = require('proxyquire').noPreserveCache();

describe('view server', function () {
  var http, instance, server, loginRoute, indexRoute, viewRouter, conf;

  beforeEach(function () {
    server = {
      listen: jasmine.createSpy('listen').and.callFake(function s () {
        return server;
      })
    };

    http = {
      createServer: jasmine.createSpy('createServer').and.returnValue(server)
    };

    viewRouter = {
      go: jasmine.createSpy('go')
    };

    conf = { viewServerPort: 8900 };

    loginRoute = jasmine.createSpy('loginRoute');
    indexRoute = jasmine.createSpy('indexRoute');

    instance = proxyquire('../../../view-server/view-server', {
      'http': http,
      './routes/login-route': loginRoute,
      './routes/index-route': indexRoute,
      './view-router': viewRouter,
      './conf': conf
    })();
  });

  it('should return a server', function () {
    expect(instance).toEqual(server);
  });

  it('should call loginRoute', function () {
    expect(loginRoute).toHaveBeenCalledOnce();
  });

  it('should call indexRoute', function () {
    expect(indexRoute).toHaveBeenCalledOnce();
  });

  it('should call createServer', function () {
    expect(http.createServer).toHaveBeenCalledOnceWith(jasmine.any(Function));
  });

  it('should listen on the view server port', function () {
    expect(server.listen).toHaveBeenCalledOnceWith(8900);
  });

  describe('routing requests', function () {
    var req, res;

    beforeEach(function () {
      req = {
        url: '/foo/bar',
        method: 'get'
      };

      res = {
        writeHead: jasmine.createSpy('writeHead'),
        end: jasmine.createSpy('end')
      };

      var handler = http.createServer.calls.mostRecent().args[0];

      handler(req, res);
    });

    it('should call the view router', function () {
      expect(viewRouter.go).toHaveBeenCalledOnceWith(req.url,
        {
          verb: req.method,
          clientReq: req
        },
        {
          clientRes: res,
          redirect: jasmine.any(Function)
        });
    });

    describe('redirecting', function () {
      beforeEach(function () {
        viewRouter.go.calls.mostRecent().args[2].redirect('/');
      });

      it('should have a method to redirect on the response object', function () {
        expect(res.writeHead).toHaveBeenCalledOnceWith(302, { Location: '/' });
      });

      it('should end the response', function () {
        expect(res.end).toHaveBeenCalledOnce();
      });
    });
  });
});
