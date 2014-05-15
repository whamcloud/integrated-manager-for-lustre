'use strict';

var Q = require('q');
var resourceFactory = require('../../../resources/resource');

describe('resource', function () {
  var Resource, conf, request, requestInstance, logger, log;

  beforeEach(function () {
    spyOn(Q, 'ninvoke').andCallThrough();
    spyOn(Q, 'spread').andCallThrough();
    spyOn(Q.makePromise.prototype, 'finally').andCallThrough();
    spyOn(Q.makePromise.prototype, 'then').andCallThrough();

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

      it('should have httpGetList work with id', function () {
        var params = {
          id: 5
        };

        resource.__httpGetList(params);

        var url = request.defaults.mostRecentCall.args[0].url;

        expect(url).toBe(conf.apiUrl + path + '/5/');
      });

      describe('metrics', function () {
        it('should provide a httpGetMetrics method', function () {
          var params = {
            qs: {
              end: '2012-03-02T11:38:49.321Z',
              begin: '2012-03-02T11:28:49.321Z'
            }
          };

          resource.__httpGetMetrics(params);

          expect(Q.ninvoke).toHaveBeenCalledOnceWith(requestInstance, 'get', {
            qs: {
              end: '2012-03-02T11:38:49.321Z',
              begin: '2012-03-02T11:28:49.321Z'
            }
          });
        });

        it('should handle id', function () {
          var params = {
            id: 5,
            qs: {
              end: '2012-03-02T11:38:49.321Z',
              begin: '2012-03-02T11:28:49.321Z'
            }
          };

          resource.__httpGetMetrics(params);

          var url = request.defaults.mostRecentCall.args[0].url;

          expect(url).toBe(conf.apiUrl + path + '/5/metric/');
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

        it('should build the path and id in the correct order', function () {
          resource.requestFor({id: 5, extraPath: 'metric'});

          var url = request.defaults.mostRecentCall.args[0].url;

          expect(url).toBe(conf.apiUrl + path + '/5/metric/');
        });

        it('should call defaults with the expected config', function () {
          resource.requestFor();

          var config = request.defaults.mostRecentCall.args[0];

          expect(config).toEqual({
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
        var params = {};

        it('should invoke request.get with params', function () {
          resource.requestFor().get(params);

          expect(Q.ninvoke).toHaveBeenCalledOnceWith(requestInstance, 'get', params);
        });

        it('should throw if resp.statusCode is >= 400', function (done) {
          requestInstance.get.andCallFake(function fake(params, cb) {
            cb(null, {
              request: {},
              statusCode: 400
            });
          });

          resource.requestFor().get(params).catch(function (err) {
            expect(err).toEqual(jasmine.any(Error));
            done();
          });
        });

        it('should return resp if resp.statusCode is < 400', function (done) {
          var serverResponse = {
            request: {},
            statusCode: 200
          };

          requestInstance.get.andCallFake(function fake(params, cb) {
            cb(null, serverResponse, {});
          });

          resource.requestFor().get(params).then(function (resp) {
            expect(resp).toEqual(serverResponse);
            done();
          });
        });

        it('should mask params', function () {
          var serverResponse = {
            request: {},
            statusCode: 200,
            body: {
              foo: 'bar',
              baz: 'bat'
            }
          };

          requestInstance.get.andCallFake(function fake (params, cb) {
            cb(null, serverResponse, serverResponse.body);
          });

          resource.requestFor().get({jsonMask: 'baz'}).then(function(resp) {
            expect(resp.body).toEqual({baz: 'bat'});
          });
        });
      });
    });
  });
});