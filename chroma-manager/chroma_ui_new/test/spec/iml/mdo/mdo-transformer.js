describe('mdo transformer', function () {
  'use strict';

  var $q, $rootScope, mdoTransformer, mdoDataFixtures, deferred;

  beforeEach(module('mdo', 'dataFixtures'));

  beforeEach(inject(function (_$q_, _$rootScope_, _mdoTransformer_, _mdoDataFixtures_) {
    mdoTransformer = _mdoTransformer_;
    mdoDataFixtures = _mdoDataFixtures_;
    $q = _$q_;
    deferred = $q.defer();
    $rootScope = _$rootScope_;
  }));

  it('should throw if resp.body is not an array', function () {
    function shouldThrow() {
      mdoTransformer({}, deferred);
    }

    expect(shouldThrow).toThrow('mdoTransformer expects resp.body to be an array!');
  });

  it('should resolve early if resp.body is an empty array', function () {
    var resp = {body: []};

    mdoTransformer(resp, deferred);

    expect(resp.body).toEqual([]);
  });

  it('should transform data as expected', function () {
    mdoDataFixtures.forEach(function (item) {
      var deferred = $q.defer();

      mdoTransformer({body: item.in}, deferred);

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