describe('get test host spark then', function () {
  'use strict';

  beforeEach(module('server'));

  var $rootScope, getTestHostSparkThen, flint, spark, deferred, promise, data, runPipeline;

  beforeEach(inject(function ($q, _$rootScope_, _getTestHostSparkThen_, _runPipeline_) {
    $rootScope = _$rootScope_;
    runPipeline = _runPipeline_;

    deferred = $q.defer();

    spark = {
      pipeline: [],
      sendPost: jasmine.createSpy('sendPost'),
      addPipe: jasmine.createSpy('addPipe').andCallFake(function (pipe) {
        this.pipeline.push(pipe);

        return this;
      }),
      onceValueThen: jasmine.createSpy('onceValueThen')
        .andReturn(deferred.promise)
    };

    flint = jasmine.createSpy('flint').andReturn(spark);

    data = {
      body: {
        objects: [
          {
            address: 'lotus-34vm5.iml.intel.com',
            status: [
              {
                name: 'auth',
                value: true
              },
              {
                name: 'reverse_ping',
                value: false
              }
            ]
          }
        ]
      }
    };

    getTestHostSparkThen = _getTestHostSparkThen_;
    promise = getTestHostSparkThen(flint, {
      objects: [ { address: 'address1' } ]
    });
  }));

  it('should be a function', function () {
    expect(getTestHostSparkThen).toEqual(jasmine.any(Function));
  });

  it('should return a promise', function () {
    expect(promise).toEqual({
      then: jasmine.any(Function),
      catch: jasmine.any(Function),
      finally: jasmine.any(Function)
    });
  });

  it('should call sendPost', function () {
    expect(spark.sendPost).toHaveBeenCalledWith('/test_host', {
      json: {
        objects: [ { address : 'address1' } ]
      }
    });
  });

  it('should resolve with the spark', function () {
    var spy = jasmine.createSpy('spy');

    promise.then(spy);

    deferred.resolve({});

    $rootScope.$digest();

    expect(spy).toHaveBeenCalledOnceWith(spark);
  });

  describe('invoking the pipe', function () {
    var response;

    beforeEach(function () {
      spark.pipeline.push(function (resp) {
        response = resp;
      });
      runPipeline(spark.pipeline, data);
    });

    it('should indicate that the response is invalid', function () {
      expect(response.body.valid).toEqual(false);
    });

    it('should have an updated response value', function () {
      expect(response).toEqual({
        body: {
          objects: [
            {
              address: 'lotus-34vm5.iml.intel.com',
              status: [
                { name : 'auth', value : true, uiName : 'Auth' },
                { name : 'reverse_ping', value : false, uiName : 'Reverse ping' }
              ]
            }
          ],
          valid : false
        }
      });
    });
  });
});
