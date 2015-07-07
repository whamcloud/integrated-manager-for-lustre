describe('append data transformer', function () {
  'use strict';

  var $rootScope, appendDataTransformer, stream, data, deferred, resp;

  beforeEach(module('charts'));

  beforeEach(inject(function ($q, _$rootScope_, _appendDataTransformer_) {
    appendDataTransformer = _appendDataTransformer_;

    $rootScope = _$rootScope_;

    data = [];

    resp = {
      body: []
    };

    deferred = $q.defer();

    stream = {
      getter: jasmine.createSpy('getter').andCallFake(function () {
        return data;
      })
    };
  }));

  it('should throw if data is not an array', function () {
    expect(shouldThrow).toThrow('Data not in expected format for appendDataTransformer!');

    function shouldThrow () {
      data = {};

      appendDataTransformer.call(stream);
    }
  });

  it('should throw if resp.body is not an array', function () {
    expect(shouldThrow).toThrow('resp.body not in expected format for appendDataTransformer!');

    function shouldThrow () {
      resp.body = {};

      appendDataTransformer.call(stream, resp);
    }
  });

  it('should push a new series if one does not exist', function () {
    var fakeSeries = {key: 'fakeKey'};

    resp.body.push(fakeSeries);

    appendDataTransformer.call(stream, resp, deferred);

    expect(data).toEqual([fakeSeries]);
  });

  it('should append values of the new series to the existing series', function () {
    var fakeSeries = {key: 'fakeKey', values: [1, 2, 3, 4]};

    resp.body.push(fakeSeries);

    data = [fakeSeries];

    appendDataTransformer.call(stream, resp, deferred);

    expect(data).toEqual([{
      key: 'fakeKey',
      values: [1,2,3,4,1,2,3,4]
    }]);
  });

  it('should resolve the deferred with data', function () {
    appendDataTransformer.call(stream, resp, deferred);

    deferred.promise.then(function (d) {
      expect(d).toBe(data);
    });

    $rootScope.$digest();
  });
});
