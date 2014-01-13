describe('read write bandwidth transformer', function () {
  'use strict';

  var $q, $rootScope, readWriteBandwidthTransformer, readWriteBandwidthDataFixtures, deferred;

  beforeEach(module('readWriteBandwidth', 'dataFixtures'));

  beforeEach(inject(function (_$q_, _$rootScope_, _readWriteBandwidthTransformer_, _readWriteBandwidthDataFixtures_) {
    readWriteBandwidthTransformer = _readWriteBandwidthTransformer_;
    readWriteBandwidthDataFixtures = _readWriteBandwidthDataFixtures_;
    $q = _$q_;
    deferred = $q.defer();
    $rootScope = _$rootScope_;
  }));

  it('should throw if resp.body is not an array', function () {
    function shouldThrow() {
      readWriteBandwidthTransformer({}, deferred);
    }

    expect(shouldThrow).toThrow('readWriteBandwidthTransformer expects resp.body to be an array!');
  });

  it('should resolve early if resp.body is an empty array', function () {
    var resp = {body: []};

    readWriteBandwidthTransformer(resp, deferred);

    expect(resp.body).toEqual([]);
  });


  it('should transform data as expected', function () {
    readWriteBandwidthDataFixtures.forEach(function (item) {
      var deferred = $q.defer();

      readWriteBandwidthTransformer({body: item.in}, deferred);

      deferred.promise.then(function (resp) {
        var data = resp.body;

        data.forEach(function (item) {
          item.values.forEach(function (value) {
            value.x = value.x.toJSON();
          });
        });

        expect(data).toEqual(item.out);
      });

      $rootScope.$digest();
    });
  });
});