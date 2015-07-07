describe('read write bandwidth stream', function () {
  'use strict';

  var ReadWriteBandwidthStream, stream, spliceOldDataTransformer, appendOrReplaceDataTransformer,
    readWriteBandwidthTransformer;

  beforeEach(module('readWriteBandwidth', function ($provide) {
    $provide.value('stream', jasmine.createSpy('stream').andCallFake(function () {
      return function ReadWriteBandwidthStream () {};
    }));
  }, {
    streamDurationMixin: {
      fakeMethod: function fakeMethod() {}
    },
    spliceOldDataTransformer: jasmine.createSpy('spliceOldDataTransformer'),
    appendOrReplaceDataTransformer: jasmine.createSpy('appendOrReplaceDataTransformer'),
    mdoTransformer: jasmine.createSpy('mdoTransformer')
  }));

  beforeEach(inject(function (_stream_, _ReadWriteBandwidthStream_, _spliceOldDataTransformer_,
                              _readWriteBandwidthTransformer_, _appendOrReplaceDataTransformer_) {
    stream = _stream_;
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
