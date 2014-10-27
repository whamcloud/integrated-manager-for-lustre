'use strict';

var wildcardRoutesFactory = require('../../../routes/wildcard-routes').wiretree;
var errorSerializer = require('bunyan').stdSerializers.err;
var _ = require('lodash-mixins');

describe('wildcard routes', function () {
  var wildcardRoutes, router, request, loop, logger;

  beforeEach(function () {
    router = {
      all: jasmine.createSpy('all')
    };

    request = {
      get: jasmine.createSpy('get').andReturn({
        then: jasmine.createSpy('then').andReturn({
          catch: jasmine.createSpy('catch').andReturn({
            done: jasmine.createSpy('done')
          })
        })
      })
    };

    loop = jasmine.createSpy('loop').andReturn(jasmine.createSpy('finish'));

    logger = {
      child: jasmine.createSpy('child').andReturn({
        info: jasmine.createSpy('info'),
        debug: jasmine.createSpy('debug')
      })
    };

    wildcardRoutes = wildcardRoutesFactory(router, request, loop, logger, _)();
  });

  it('should register a wildcard handler', function () {
    expect(router.all).toHaveBeenCalledOnceWith('/(.*)', jasmine.any(Function));
  });

  describe('calling the route handler', function () {
    var handler, req, resp, err;

    beforeEach(function () {
      handler = router.all.mostRecentCall.args[1];

      req = {
        matches: ['/foo'],
        verb: 'get',
        data: {}
      };

      resp = {
        spark: {
          getResponseFormat: jasmine.createSpy('getResponseFormat').andCallFake(function (statusCode, body) {
            return {
              statusCode: statusCode,
              body: body
            };
          }),
          getErrorFormat: jasmine.createSpy('getErrorFormat').andCallFake(function (statusCode, error) {
            return {
              statusCode: statusCode,
              error: errorSerializer(error)
            };
          }),
          writeResponse: jasmine.createSpy('writeResponse'),
          writeError: jasmine.createSpy('writeError'),
          removeAllListeners: jasmine.createSpy('removeAllListeners'),
          on: jasmine.createSpy('on')
        }
      };

      err = new Error('boom!');
      err.statusCode = 400;
    });

    describe('with ack', function () {
      beforeEach(function () {
        resp.ack = jasmine.createSpy('ack');
        handler(req, resp);
      });

      it('should ack a response', function () {
        request.get.plan().then.mostRecentCall.args[0]({
          statusCode: 200,
          body: { foo: 'bar' }
        });

        expect(resp.ack).toHaveBeenCalledOnceWith({
          statusCode: 200,
          body: { foo : 'bar' }
        });
      });

      it('should ack an error', function () {
        request.get.plan().then.plan().catch.mostRecentCall.args[0](err);

        expect(resp.ack).toHaveBeenCalledOnceWith({
          statusCode: 400,
          error : { message : 'boom!', name : 'Error', stack: jasmine.any(String) }
        });
      });
    });

    describe('without ack', function () {
      var next;

      beforeEach(function () {
        handler(req, resp);

        next = jasmine.createSpy('next');
        loop.mostRecentCall.args[0](next);
      });

      it('should start a loop', function () {
        expect(loop).toHaveBeenCalledOnce();
      });

      it('should write a response', function () {
        request.get.plan().then.mostRecentCall.args[0]({
          statusCode: 200,
          body: { foo : 'bar' }
        });

        expect(resp.spark.writeResponse).toHaveBeenCalledOnceWith(200, { foo: 'bar' });
      });

      it('should write an error', function () {
        request.get.plan().then.plan().catch.mostRecentCall.args[0](err);

        expect(resp.spark.writeError).toHaveBeenCalledOnceWith(400, err);
      });

      it('should invoke done with the next turn when looping', function () {
        expect(request.get.plan().then.plan().catch.plan().done).toHaveBeenCalledOnceWith(next, next);
      });

      it('should register an end listener on the spark when looping', function () {
        expect(resp.spark.on).toHaveBeenCalledOnceWith('end', jasmine.any(Function));
      });

      it('should remove all listeners on ending', function () {
        resp.spark.on.mostRecentCall.args[1]();

        expect(resp.spark.removeAllListeners).toHaveBeenCalledOnce();
      });

      it('should finish the loop', function () {
        resp.spark.on.mostRecentCall.args[1]();

        expect(loop.plan()).toHaveBeenCalledOnce();
      });
    });
  });
});
