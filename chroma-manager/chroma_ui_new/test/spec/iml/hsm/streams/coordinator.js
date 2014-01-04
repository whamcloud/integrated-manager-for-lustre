describe('HSM coordinator stream', function () {
  'use strict';

  var HsmCdtStream, stream, spliceOldDataTransformer, appendOrReplaceDataTransformer, hsmCdtTransformer,
    streamDurationMixin;

  beforeEach(module('hsm'));

  mock.beforeEach(
    function createStreamMock() {
      stream = jasmine.createSpy('stream').andCallFake(function () {
        return function streamInstance() {};
      });

      return {
        name: 'stream',
        value: stream
      };
    },
    function createStreamDurationMixinMock() {
      streamDurationMixin = {
        fakeMethod: function () {}
      };

      return {
        name: 'streamDurationMixin',
        value: streamDurationMixin
      };
    }
  );

  beforeEach(inject(function (_HsmCdtStream_, _spliceOldDataTransformer_,
                              _hsmCdtTransformer_, _appendOrReplaceDataTransformer_) {
    HsmCdtStream = _HsmCdtStream_;
    spliceOldDataTransformer = _spliceOldDataTransformer_;
    hsmCdtTransformer = _hsmCdtTransformer_;
    appendOrReplaceDataTransformer = _appendOrReplaceDataTransformer_;
  }));

  it('should configure the stream', function () {
    var expectedConfig = {
      params: {
        qs: {
          reduce_fn: 'sum',
          role: 'MDT',
          metrics: 'hsm_actions_waiting,hsm_actions_running,hsm_agents_idle'
        }
      },
      transformers: [spliceOldDataTransformer, hsmCdtTransformer, appendOrReplaceDataTransformer]
    };

    expect(stream).toHaveBeenCalledOnceWith('target', 'httpGetMetrics', expectedConfig);
  });

  it('should have streamDurationMixin methods', function () {
    expect(HsmCdtStream.prototype.fakeMethod).toEqual(jasmine.any(Function));
  });
});
