describe('ost-balance-transformer', function () {
  'use strict';

  var $q, $rootScope, deferred, ostBalanceTransformer, ostBalanceDataFixtures, stream;

  beforeEach(module('ostBalance', 'dataFixtures'));

  beforeEach(inject(function (_$q_, _ostBalanceTransformer_, _ostBalanceDataFixtures_, _$rootScope_) {
    $q = _$q_;
    deferred = $q.defer();
    $rootScope = _$rootScope_;
    ostBalanceTransformer = _ostBalanceTransformer_;
    ostBalanceDataFixtures = _ostBalanceDataFixtures_;

    stream = {};
  }));

  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      var deferred = $q.defer();

      ostBalanceTransformer.call(stream, {}, deferred);
    }

    expect(shouldThrow).toThrow('ostBalanceTransformer expects resp.body to be an object!');
  });

  it('should transform data', function () {
    ostBalanceDataFixtures.forEach(function (item) {
      var deferred = $q.defer();

      ostBalanceTransformer.call(stream, {body: item.in}, deferred);

      deferred.promise.then(function (resp) {
        expect(resp.body).toEqual(item.out);
      });

      $rootScope.$digest();
    });
  });
});