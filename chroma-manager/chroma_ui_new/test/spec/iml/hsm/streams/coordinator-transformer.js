describe('HSM coordinator transformer', function () {
  'use strict';

  var $q, $rootScope, hsmCdtTransformer, hsmCdtDataFixtures, deferred;

  beforeEach(module('hsm', 'dataFixtures'));

  beforeEach(inject(function (_$q_, _$rootScope_, _hsmCdtTransformer_, _hsmCdtDataFixtures_) {
    hsmCdtTransformer = _hsmCdtTransformer_;
    hsmCdtDataFixtures = _hsmCdtDataFixtures_;
    $q = _$q_;
    deferred = $q.defer();
    $rootScope = _$rootScope_;
  }));

  it('should throw if resp.body is not an array', function () {
    function shouldThrow() {
      hsmCdtTransformer({}, deferred);
    }

    expect(shouldThrow).toThrow('Transformer expects resp.body to be an array!');
  });

  it('should resolve early if resp.body is an empty array', function () {
    var resp = {body: []};

    hsmCdtTransformer(resp, deferred);

    expect(resp.body).toEqual([]);
  });


  it('should transform data as expected', function () {
    hsmCdtDataFixtures.forEach(function (item) {
      var deferred = $q.defer();

      hsmCdtTransformer({body: item.in}, deferred);

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
