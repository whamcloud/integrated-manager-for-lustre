describe('HSM copytoolOperation stream transformer', function () {
  'use strict';

  var HsmCopytoolOperationModel,
      hsmCopytoolOperationStreamTransformer,
      hsmCopytoolOperationStreamDataFixtures;

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

  beforeEach(inject(function (_$rootScope_,
                              _hsmCopytoolOperationStreamTransformer_,
                              _hsmCopytoolOperationStreamDataFixtures_) {
    hsmCopytoolOperationStreamTransformer = _hsmCopytoolOperationStreamTransformer_;
    hsmCopytoolOperationStreamDataFixtures = _hsmCopytoolOperationStreamDataFixtures_;
  }));

  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      hsmCopytoolOperationStreamTransformer([]);
    }

    expect(shouldThrow).toThrow('hsmCopytoolOperationStreamTransformer expects resp.body to be an object!');
  });

  it('should resolve early if resp.body.objects is an empty array', function () {
    var resp = {body: {objects: []}};

    hsmCopytoolOperationStreamTransformer(resp);

    expect(resp.body.objects).toEqual([]);
  });

  it('should transform the objects list as expected', function () {
    hsmCopytoolOperationStreamDataFixtures.forEach(function (item) {
      var preTransformMeta = _.cloneDeep(item.body.meta);

      hsmCopytoolOperationStreamTransformer(item);

      expect(HsmCopytoolOperationModel.calls.length).toEqual(item.body.objects.length);

      // Ensure that the transformer doesn't mess with anything outside
      // the objects list.
      expect(item.body.meta).toEqual(preTransformMeta);
    });
  });
});
