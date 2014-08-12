'use strict';

var resourceFactory = require('../../../resources/resource');

describe('resource', function () {
  var Resource, request, logger, log;

  beforeEach(function () {
    log = {
      info: jasmine.createSpy('log.info'),
      debug: jasmine.createSpy('log.debug'),
      trace: jasmine.createSpy('log.trace')
    };

    request = {
      get: jasmine.createSpy('request')
    };

    logger = {
      child: jasmine.createSpy('logger.child').andReturn(log)
    };

    Resource = resourceFactory(request, logger);
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
    var resource;
    var path = 'foo';

    beforeEach(function () {
      resource = new Resource(path);
    });

    it('should create a logger', function () {
      expect(logger.child).toHaveBeenCalledOnceWith({resource: 'Resource'});
    });

    it('should make the logger available', function () {
      expect(resource.log).toBe(log);
    });

    it('should set the path', function () {
      expect(resource.path).toBe(path);
    });

    it('should set the request', function () {
      expect(resource.request).toEqual({
        get: jasmine.any(Function)
      });
    });

    describe('httpMethods', function () {
      it('should provide a httpGetList method', function () {
        var options = {foo: 'bar'};

        resource.__httpGetList(options);

        expect(request.get).toHaveBeenCalledOnceWith(path, options);
      });

      it('should have httpGetList work with id', function () {
        var options = { id: 5 };

        resource.__httpGetList(options);

        expect(request.get).toHaveBeenCalledOnceWith(path + '/5', {});
      });

      describe('metrics', function () {
        it('should provide a httpGetMetrics method', function () {
          var options = {
            qs: {
              end: '2012-03-02T11:38:49.321Z',
              begin: '2012-03-02T11:28:49.321Z'
            }
          };

          resource.__httpGetMetrics(options);

          expect(request.get).toHaveBeenCalledOnceWith(path + '/metric', options);
        });

        it('should handle id', function () {
          var options = {
            id: 5,
            qs: {
              end: '2012-03-02T11:38:49.321Z',
              begin: '2012-03-02T11:28:49.321Z'
            }
          };

          resource.__httpGetMetrics(options);

          expect(request.get).toHaveBeenCalledOnceWith(path + '/5/metric', {
            qs: options.qs
          });
        });
      });

      describe('request for', function () {
        it('should provide a way to expand the path', function () {
          var wrappedRequest = resource.requestFor({extraPath: 'hello'});

          wrappedRequest.get({});

          expect(request.get).toHaveBeenCalledOnceWith(path + '/hello', {});
        });

        it('should provide a way to add an id', function () {
          var wrappedRequest = resource.requestFor({id: 5});

          wrappedRequest.get({});

          expect(request.get).toHaveBeenCalledOnceWith(path + '/5', {});
        });

        it('should build the path and id in the correct order', function () {
          var wrappedRequest = resource.requestFor({id: 5, extraPath: 'metric'});

          wrappedRequest.get({});

          expect(request.get).toHaveBeenCalledOnceWith(path + '/5/metric', {});
        });
      });
    });
  });
});
