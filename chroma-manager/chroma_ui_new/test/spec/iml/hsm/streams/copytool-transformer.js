describe('HSM copytool stream transformer', function () {
  'use strict';

  var HsmCopytoolModel, hsmCopytoolStreamTransformer,
      hsmCopytoolStreamDataFixtures;

  beforeEach(module('hsm', 'dataFixtures', 'modelFactory'));

  mock.beforeEach(
    function createHsmCopytoolModelMock() {
      HsmCopytoolModel = jasmine.createSpy('HsmCopytoolModel');

      return {
        name: 'HsmCopytoolModel',
        value: HsmCopytoolModel
      };
    }
  );

  beforeEach(inject(function (_hsmCopytoolStreamTransformer_,
                              _hsmCopytoolStreamDataFixtures_) {
    hsmCopytoolStreamTransformer = _hsmCopytoolStreamTransformer_;
    hsmCopytoolStreamDataFixtures = _hsmCopytoolStreamDataFixtures_;
  }));

  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      hsmCopytoolStreamTransformer([]);
    }

    expect(shouldThrow).toThrow('hsmCopytoolStreamTransformer expects resp.body to be an object!');
  });

  it('should resolve early if resp.body.objects is an empty array', function () {
    var resp = {body: {objects: []}};

    hsmCopytoolStreamTransformer(resp);

    expect(resp.body.objects).toEqual([]);
  });

  it('should transform the objects list as expected', function () {
    hsmCopytoolStreamDataFixtures.forEach(function (item) {
      var preTransformMeta = _.cloneDeep(item.body.meta);

      hsmCopytoolStreamTransformer(item);

      expect(HsmCopytoolModel.calls.length).toEqual(item.body.objects.length);

      // Ensure that the transformer doesn't mess with anything outside
      // the objects list.
      expect(item.body.meta).toEqual(preTransformMeta);
    });
  });
});
