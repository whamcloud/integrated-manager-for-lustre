describe('mds transformer', function () {
  'use strict';

  var $q, $rootScope, mdsTransformer, mdsDataFixtures, deferred;

  beforeEach(module('mds', 'dataFixtures'));

  beforeEach(inject(function (_$q_, _$rootScope_, _mdsTransformer_, _mdsDataFixtures_) {
    mdsTransformer = _mdsTransformer_;
    mdsDataFixtures = _mdsDataFixtures_;
    $q = _$q_;
    deferred = $q.defer();
    $rootScope = _$rootScope_;
  }));

  it('should throw if resp.body is not an array', function () {
    function shouldThrow() {
      mdsTransformer({}, deferred);
    }

    expect(shouldThrow).toThrow('mdsTransformer expects resp.body to be an array!');
  });

  it('should resolve early if resp.body is an empty array', function () {
    var resp = {body: []};

    mdsTransformer(resp, deferred);

    expect(resp.body).toEqual([]);
  });


  it('should transform data as expected', function () {
    mdsDataFixtures.forEach(function (item) {
      var deferred = $q.defer();

      mdsTransformer({body: item.in}, deferred);

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