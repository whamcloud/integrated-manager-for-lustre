describe('HSM copytool stream', function () {
  'use strict';

  var HsmCopytoolStream, stream, hsmCopytoolStreamTransformer,
      replaceTransformer;

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

  beforeEach(inject(function (_HsmCopytoolStream_,
                              _hsmCopytoolStreamTransformer_,
                              _replaceTransformer_) {
    HsmCopytoolStream = _HsmCopytoolStream_;
    hsmCopytoolStreamTransformer = _hsmCopytoolStreamTransformer_;
    replaceTransformer = _replaceTransformer_;
  }));

  it('should configure the stream', function () {
    var expectedConfig = {
      transformers: [hsmCopytoolStreamTransformer, replaceTransformer]
    };

    expect(stream).toHaveBeenCalledOnceWith('copytool', 'httpGetList', expectedConfig);
  });
});
