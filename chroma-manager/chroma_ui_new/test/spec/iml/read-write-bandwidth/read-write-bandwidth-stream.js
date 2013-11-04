describe('read write bandwidth stream', function () {
  'use strict';

  var ReadWriteBandwidthStream, stream, spliceOldDataTransformer, appendOrReplaceDataTransformer,
    readWriteBandwidthTransformer, streamDurationMixin;

  beforeEach(module('readWriteBandwidth'));

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

  beforeEach(inject(function (_ReadWriteBandwidthStream_, _spliceOldDataTransformer_,
                              _readWriteBandwidthTransformer_, _appendOrReplaceDataTransformer_) {
    ReadWriteBandwidthStream = _ReadWriteBandwidthStream_;
    spliceOldDataTransformer = _spliceOldDataTransformer_;
    readWriteBandwidthTransformer = _readWriteBandwidthTransformer_;
    appendOrReplaceDataTransformer = _appendOrReplaceDataTransformer_;
  }));

  it('should configure the stream', function () {
    var expectedConfig = {
      params: {
        qs: {
          reduce_fn: 'sum',
          kind: 'OST',
          metrics: 'stats_read_bytes,stats_write_bytes'
        }
      },
      transformers: [spliceOldDataTransformer, readWriteBandwidthTransformer, appendOrReplaceDataTransformer]
    };

    expect(stream).toHaveBeenCalledOnceWith('target', 'httpGetMetrics', expectedConfig);
  });

  it('should have streamDurationMixin methods', function () {
    expect(ReadWriteBandwidthStream.prototype.fakeMethod).toEqual(jasmine.any(Function));
  });
});