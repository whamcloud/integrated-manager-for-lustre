describe('HSM copytoolOperation stream', function () {
  'use strict';

  var HsmCopytoolOperationStream, stream, hsmCopytoolOperationStreamTransformer,
      replaceTransformer, modelFactory;

  beforeEach(module('hsm', 'modelFactory'));

  mock.beforeEach(
    function createStreamMock() {
      stream = jasmine.createSpy('stream').andCallFake(function () {
        return function streamInstance() {};
      });

      return {
        name: 'stream',
        value: stream
      };
    }
  );

  beforeEach(inject(function (_HsmCopytoolOperationStream_,
                              _hsmCopytoolOperationStreamTransformer_,
                              _replaceTransformer_, _modelFactory_) {
    HsmCopytoolOperationStream = _HsmCopytoolOperationStream_;
    hsmCopytoolOperationStreamTransformer = _hsmCopytoolOperationStreamTransformer_;
    replaceTransformer = _replaceTransformer_;
    modelFactory = _modelFactory_;
  }));

  it('should configure the stream', function () {
    var expectedConfig = {
      params: {
        qs: {
          active: true
        }
      },
      transformers: [hsmCopytoolOperationStreamTransformer, replaceTransformer]
    };

    expect(stream).toHaveBeenCalledOnceWith('copytool_operation', 'httpGetList', expectedConfig);
  });
});
