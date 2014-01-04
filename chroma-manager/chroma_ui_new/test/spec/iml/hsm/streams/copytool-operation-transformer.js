describe('HSM copytoolOperation stream transformer', function () {
  'use strict';

  var $q, $rootScope, HsmCopytoolOperationModel,
      hsmCopytoolOperationStreamTransformer,
      hsmCopytoolOperationStreamDataFixtures, deferred;

  beforeEach(module('hsm', 'dataFixtures', 'modelFactory'));

  mock.beforeEach(
    function createHsmCopytoolOperationModelMock() {
      HsmCopytoolOperationModel = jasmine.createSpy('HsmCopytoolOperationModel');

      return {
        name: 'HsmCopytoolOperationModel',
        value: HsmCopytoolOperationModel
      };
    }
  );

  beforeEach(inject(function (_$q_, _$rootScope_,
                              _hsmCopytoolOperationStreamTransformer_,
                              _hsmCopytoolOperationStreamDataFixtures_) {
    hsmCopytoolOperationStreamTransformer = _hsmCopytoolOperationStreamTransformer_;
    hsmCopytoolOperationStreamDataFixtures = _hsmCopytoolOperationStreamDataFixtures_;
    $q = _$q_;
    deferred = $q.defer();
    $rootScope = _$rootScope_;
  }));

  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      hsmCopytoolOperationStreamTransformer([], deferred);
    }

    expect(shouldThrow).toThrow('hsmCopytoolOperationStreamTransformer expects resp.body to be an object!');
  });

  it('should resolve early if resp.body.objects is an empty array', function () {
    var resp = {body: {objects: []}};

    hsmCopytoolOperationStreamTransformer(resp, deferred);

    expect(resp.body.objects).toEqual([]);
  });

  it('should transform the objects list as expected', function () {
    hsmCopytoolOperationStreamDataFixtures.forEach(function (item) {
      var deferred = $q.defer();
      var preTransformMeta = _.cloneDeep(item.body.meta);

      hsmCopytoolOperationStreamTransformer(item, deferred);

      deferred.promise.then(function () {
        expect(HsmCopytoolOperationModel.calls.length).toEqual(item.body.objects.length);

        // Ensure that the transformer doesn't mess with anything outside
        // the objects list.
        expect(item.body.meta).toEqual(preTransformMeta);
      });

      $rootScope.$digest();
    });
  });
});
