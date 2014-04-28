describe('Target', function () {
  'use strict';

  beforeEach(module('target', {
    stream: jasmine.createSpy('stream').andReturn(TargetStream),
    beforeStreamingDuration: jasmine.createSpy('beforeStreamingDuration')
  }));

  // The constructor returned by a call to stream
  function TargetStream() {}

  var replaceTransformer, stream, beforeStreamingDuration;

  beforeEach(inject(function (_TargetStream_, _replaceTransformer_, _stream_, _beforeStreamingDuration_) {
    replaceTransformer = _replaceTransformer_;
    stream = _stream_;
    beforeStreamingDuration = _beforeStreamingDuration_;
  }));

  it('should setup the stream', function () {
    expect(stream).toHaveBeenCalledOnceWith('target', 'httpGetList', {
      transformers: [replaceTransformer]
    });

    expect(TargetStream.prototype.beforeStreaming).toBe(beforeStreamingDuration);
  });
});