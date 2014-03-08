'use strict';

var sinon = require('sinon'),
  resourceFactory = require('../../../resources/resource');

describe('resource', function () {
  var Resource, conf, request, requestInstance, logger, log, Q, clock;

  beforeEach(function () {
    Q = {
      ninvoke: jasmine.createSpy('Q.ninvoke').andReturn({
        spread: jasmine.createSpy('Q.ninvoke.spread')
      })
    };

    clock = sinon.useFakeTimers(1330688329321);

    log = {
      info: jasmine.createSpy('log.info'),
      debug: jasmine.createSpy('log.debug'),
      trace: jasmine.createSpy('log.trace')
    };

    conf = {
      apiUrl: 'https://fake.com/api/',
      caFile: 'blah'
    };

    requestInstance = {
      get: jasmine.createSpy('request')
    };

    logger = {
      child: jasmine.createSpy('logger.child').andReturn(log)
    };

    request = {
      defaults: jasmine.createSpy('request.defaults').andReturn(requestInstance)
    };

    Resource = resourceFactory(conf, request, logger, Q);
  });

  afterEach(function () {
    clock.restore();
  });

  it('should throw if path is not passed', function () {
    function shouldThrow () {
      new Resource();
    }

    expect(shouldThrow).toThrow();
  });

  it('should map defaults to resource methods', function () {
    Resource.prototype.defaults = ['GetList'];

    var resource = new Resource('foo');

    expect(resource.httpGetList).toEqual(jasmine.any(Function));
  });

  it('should provide a method that lists httpMethods', function () {
    Resource.prototype.defaults = ['GetList'];

    var resource = new Resource('foo');

    expect(resource.getHttpMethods()).toEqual(['httpGetList']);
  });

  describe('instantiation', function () {
    var path = 'foo',
      resource;

    beforeEach(function () {
      resource = new Resource(path);
    });

    it('should create a logger', function () {
      expect(logger.child).toHaveBeenCalledOnceWith({resource: 'Resource'});
    });

    it('should make the logger available', function () {
      expect(resource.log).toBe(log);
    });

    it('should set the baseUrl', function () {
      expect(resource.baseUrl).toBe(conf.apiUrl + path);
    });

    it('should set the request', function () {
      expect(resource.request).toEqual({
        get: jasmine.any(Function)
      });
    });

    describe('httpMethods', function () {
      it('should provide a httpGetList method', function () {
        var params = {foo: 'bar'};

        resource.__httpGetList(params);

        expect(Q.ninvoke).toHaveBeenCalledOnceWith(requestInstance, 'get', params);
      });

      it('should provide a httpGetMetrics method', function () {
        var params = {
          qs: {
            size: 10,
            unit: 'minutes'
          }
        };

        resource.__httpGetMetrics(params);

        expect(Q.ninvoke).toHaveBeenCalledOnceWith(requestInstance, 'get', {
          qs: {
            end: '2012-03-02T11:38:49.321Z',
            begin: '2012-03-02T11:28:49.321Z',
            size: 10,
            unit: 'minutes'
          }
        });
      });

      describe('request for', function () {
        it('should provide a way to expand the path', function () {
          resource.requestFor({extraPath: 'hello'});

          var url = request.defaults.mostRecentCall.args[0].url;

          expect(url).toBe(conf.apiUrl + path + '/' + 'hello/');
        });

        it('should provide a way to add an id', function () {
          resource.requestFor({id: 5});

          var url = request.defaults.mostRecentCall.args[0].url;

          expect(url).toBe(conf.apiUrl + path + '/5/');
        });

        it('should call defaults with the expected config', function () {
          resource.requestFor();

          var config = request.defaults.mostRecentCall.args[0];

          expect(config).toEqual({
            jar: true,
            json: true,
            ca: conf.caFile,
            url: conf.apiUrl + path + '/',
            strictSSL: false,
            maxSockets: 25,
            forever: true,
            timeout: 120000
          });
        });
      });

      describe('get handling', function () {
        var params = {}, spread;

        beforeEach(function () {
          resource.requestFor().get(params);

          spread = Q.ninvoke.plan().spread.mostRecentCall.args[0];
        });

        it('should invoke request.get with params', function () {
          expect(Q.ninvoke).toHaveBeenCalledOnceWith(requestInstance, 'get', params);
        });

        it('should throw if resp.statusCode is >= 400', function () {
          var resp = {
            request: {},
            statusCode: 400
          };

          function shouldThrow() {
            spread(resp, {});
          }

          expect(shouldThrow).toThrow();
        });

        it('should return resp if resp.statusCode is < 400', function () {
          var resp = {
            request: {},
            statusCode: 200
          };

          var result = spread(resp, {});

          expect(result).toBe(resp);
        });
      });
    });
  });
});