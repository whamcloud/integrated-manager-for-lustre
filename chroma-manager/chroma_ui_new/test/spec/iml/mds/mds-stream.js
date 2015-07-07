describe('mds stream', function () {
  'use strict';

  var MdsStream, stream, spliceOldDataTransformer, appendOrReplaceDataTransformer, mdsTransformer;

  beforeEach(module('mds', function ($provide) {
    $provide.value('stream', jasmine.createSpy('stream').andCallFake(function () {
      return function MdsStream () {};
    }));
  }, {
    streamDurationMixin: {
      fakeMethod: function fakeMethod() {}
    },
    spliceOldDataTransformer: jasmine.createSpy('spliceOldDataTransformer'),
    appendOrReplaceDataTransformer: jasmine.createSpy('appendOrReplaceDataTransformer'),
    mdoTransformer: jasmine.createSpy('mdoTransformer')
  }));

  beforeEach(inject(function (_stream_, _MdsStream_, _spliceOldDataTransformer_,
                              _mdsTransformer_, _appendOrReplaceDataTransformer_) {
    stream = _stream_;
    MdsStream = _MdsStream_;
    spliceOldDataTransformer = _spliceOldDataTransformer_;
    mdsTransformer = _mdsTransformer_;
    appendOrReplaceDataTransformer = _appendOrReplaceDataTransformer_;
  }));

  it('should configure the stream', function () {
    var expectedConfig = {
      params: {
        qs: {
          reduce_fn: 'average',
          role: 'MDS',
          metrics: 'cpu_total,cpu_user,cpu_system,cpu_iowait,mem_MemFree,mem_MemTotal'
        }
      },
      transformers: [spliceOldDataTransformer, mdsTransformer, appendOrReplaceDataTransformer]
    };

    expect(stream).toHaveBeenCalledOnceWith('host', 'httpGetMetrics', expectedConfig);
  });

  it('should have streamDurationMixin methods', function () {
    expect(MdsStream.prototype.fakeMethod).toEqual(jasmine.any(Function));
  });
});
