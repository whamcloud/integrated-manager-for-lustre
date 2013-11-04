describe('mdo stream', function () {
  'use strict';

  var MdoStream, stream, spliceOldDataTransformer, appendOrReplaceDataTransformer, mdoTransformer,
    streamDurationMixin;

  beforeEach(module('mdo'));

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

  beforeEach(inject(function (_MdoStream_, _spliceOldDataTransformer_,
                              _mdoTransformer_, _appendOrReplaceDataTransformer_) {
    MdoStream = _MdoStream_;
    spliceOldDataTransformer = _spliceOldDataTransformer_;
    mdoTransformer = _mdoTransformer_;
    appendOrReplaceDataTransformer = _appendOrReplaceDataTransformer_;
  }));

  it('should configure the stream', function () {
    var expectedConfig = {
      params: {
        qs: {
          reduce_fn: 'sum',
          kind: 'MDT',
          metrics: 'stats_close,stats_getattr,stats_getxattr,stats_link,stats_mkdir,stats_mknod,stats_open,\
stats_rename,stats_rmdir,stats_setattr,stats_statfs,stats_unlink'
        }
      },
      transformers: [spliceOldDataTransformer, mdoTransformer, appendOrReplaceDataTransformer]
    };

    expect(stream).toHaveBeenCalledOnceWith('target', 'httpGetMetrics', expectedConfig);
  });

  it('should have streamDurationMixin methods', function () {
    expect(MdoStream.prototype.fakeMethod).toEqual(jasmine.any(Function));
  });
});