'use strict';

var requestChannelFactory = require('../../request-channel');

describe('request channel', function () {

  var primus, spark, router, routes, logger, requestChannelValidator;

  beforeEach(function () {
    primus = {
      channel: jasmine.createSpy('channel').andReturn({
        on: jasmine.createSpy('on')
      })
    };

    spark = {
      on: jasmine.createSpy('on'),
      writeError: jasmine.createSpy('write'),
      getErrorFormat: jasmine.createSpy('getErrorFormat').andCallFake(function (status, err) {
        return {
          statusCode: status,
          error: err
        };
      })
    };

    router = {
      go: jasmine.createSpy('go')
    };

    routes = jasmine.createSpy('routes');

    logger = {
      info: jasmine.createSpy('info')
    };

    requestChannelValidator = jasmine.createSpy('requestChannelValidator').andReturn([]);

    requestChannelFactory(primus, router, routes, logger, requestChannelValidator)();
  });

  it('should open a request channel', function () {
    expect(primus.channel).toHaveBeenCalledOnceWith('request');
  });

  it('should listen for connections', function () {
    expect(primus.channel.plan().on).toHaveBeenCalledOnceWith('connection', jasmine.any(Function));
  });

  describe('working with the spark', function () {
    var ack;

    beforeEach(function () {
      primus.channel.plan().on.calls[0].args[1](spark);
      ack = jasmine.createSpy('ack');
    });

    it('should listen for a request', function () {
      expect(spark.on).toHaveBeenCalledOnceWith('req', jasmine.any(Function));
    });

    it('should pass valid data to the router', function () {
      spark.on.calls[0].args[1]({
        path: 'foo'
      });

      expect(router.go).toHaveBeenCalledOnceWith('foo', 'get', spark, {}, undefined);
    });

    it('should pass valid data to the router with an ack', function () {
      spark.on.calls[0].args[1]({
        path: 'foo'
      }, ack);

      expect(router.go).toHaveBeenCalledOnceWith('foo', 'get', spark, {}, ack);
    });

    it('should ack an error if validation fails', function () {
      requestChannelValidator.andReturn([new Error('foo')]);

      spark.on.calls[0].args[1]([], ack);

      expect(ack).toHaveBeenCalledOnceWith({
        statusCode: 400,
        error: jasmine.any(Error)
      });
    });

    it('should write an error on the spark if validation fails', function () {
      requestChannelValidator.andReturn([new Error('foo')]);

      spark.on.calls[0].args[1]([]);

      expect(spark.writeError).toHaveBeenCalledOnceWith(400, jasmine.any(Error));
    });
  });
});
