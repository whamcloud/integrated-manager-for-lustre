describe('replace transformer', function () {
  'use strict';

  var $rootScope, replaceTransformer, stream, data, deferred, resp;

  beforeEach(module('stream'));

  beforeEach(inject(function ($q, _$rootScope_, _replaceTransformer_) {
    replaceTransformer = _replaceTransformer_;

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

  it('should replace the data with the response.body', function () {
    var fakeRecord = {};

    resp.body = [fakeRecord];

    replaceTransformer.call(stream, resp, deferred);

    expect(data).toEqual([fakeRecord]);
  });

  it('should resolve with the data', function () {
    replaceTransformer.call(stream, resp, deferred);

    deferred.promise.then(function (d) {
      expect(d).toBe(data);
    });

    $rootScope.$digest();
  });

  it('should preserve object identity', function () {
    function FakeThingy () {};

    resp.body = [new FakeThingy()];

    replaceTransformer.call(stream, resp, deferred);

    expect(data[0].constructor).toEqual(FakeThingy);
  });
});
