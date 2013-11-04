'use strict';

var sinon = require('sinon'),
  resourceFactory = require('../../../resources/resource');

require('jasmine-sinon');

describe('resource', function () {
  var Resource, conf, request, requestInstance, logger, log, clock;

  beforeEach(function () {
    log = sinon.spy();

    clock = sinon.useFakeTimers(1330688329321);

    conf = {
      apiUrl: 'https://fake.com/api/',
      caFile: 'blah'
    };

    requestInstance = {
      get: sinon.spy()
    };

    logger = {
      child: sinon.stub().returns(log)
    };

    request = {
      defaults: sinon.stub().returns(requestInstance)
    };

    Resource = resourceFactory(conf, request, logger);
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
      expect(logger.child).toHaveBeenAlwaysCalledWith({resource: 'Resource'});
    });

    it('should make the logger available', function () {
      expect(resource.log).toBe(log);
    });

    it('should set the baseUrl', function () {
      expect(resource.baseUrl).toBe(conf.apiUrl + path);
    });

    it('should set the request', function () {
      expect(resource.request).toBe(requestInstance);
    });

    describe('httpMethods', function () {
      it('should provide a httpGetList method', function () {
        var params = {foo: 'bar'};

        resource.__httpGetList(params, function () {});

        expect(requestInstance.get).toHaveBeenAlwaysCalledWith(params, sinon.match.func);
      });

      it('should provide a httpGetMetrics method', function () {
        var params = {
          qs: {
            size: 10,
            unit: 'minutes'
          }
        };

        resource.__httpGetMetrics(params, function () {});

        expect(requestInstance.get).toHaveBeenAlwaysCalledWith({
          qs: {
            end: '2012-03-02T11:38:49.321Z',
            begin: '2012-03-02T11:28:49.321Z',
            size: 10,
            unit: 'minutes'
          }
        }, sinon.match.func);
      });

      describe('request for', function () {
        it('should provide a way to expand the path', function () {
          resource.requestFor({extraPath: 'hello'});

          var config = request.defaults.getCall(1).args[0];

          expect(config.url).toBe(conf.apiUrl + path + '/' + 'hello/');
        });

        it('should provide a way to add an id', function () {
          resource.requestFor({id: 5});

          var config = request.defaults.getCall(1).args[0];

          expect(config.url).toBe(conf.apiUrl + path + '/5/');
        });

        it('should call defaults with the expected config', function () {
          resource.requestFor();

          var config = request.defaults.getCall(1).args[0];

          expect(config).toEqual({
            jar: true,
            json: true,
            ca: conf.caFile,
            url: conf.apiUrl + path + '/',
            strictSSL: false
          });
        });
      });

      describe('generic GET handler', function () {
        var genericGetHandler, cb, params;

        beforeEach(function () {
          cb = sinon.spy();
          params = {};

          genericGetHandler = resource.createGenericGetHandler(cb, params);
        });

        it('should call with an error', function () {
          var err = new Error('boom!');

          genericGetHandler(err);

          expect(cb).toHaveBeenAlwaysCalledWith({error: err});
        });

        it('should call with an error if resp is >= 400', function () {
          genericGetHandler(null, {statusCode: 500}, []);

          expect(cb).toHaveBeenAlwaysCalledWith({error: [], status: 500});
        });

        it('should call when there is no error', function () {
          genericGetHandler(null, {statusCode: 200}, []);

          expect(cb).toHaveBeenAlwaysCalledWith(null, {statusCode: 200}, [], params);
        });
      });
    });
  });
});