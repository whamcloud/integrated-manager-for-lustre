describe('Host', function () {
  'use strict';

  beforeEach(module('host', {
    stream: jasmine.createSpy('stream').andReturn(HostStream),
    beforeStreamingDuration: jasmine.createSpy('beforeStreamingDuration')
  }));

  // The constructor returned by a call to stream
  function HostStream() {}

  var replaceTransformer, stream, beforeStreamingDuration;

  beforeEach(inject(function (_HostStream_, _replaceTransformer_, _stream_, _beforeStreamingDuration_) {
    replaceTransformer = _replaceTransformer_;
    stream = _stream_;
    beforeStreamingDuration = _beforeStreamingDuration_;
  }));

  it('should setup the stream', function () {
    expect(stream).toHaveBeenCalledOnceWith('host', 'httpGetList', {
      transformers: [replaceTransformer]
    });

    expect(HostStream.prototype.beforeStreaming).toBe(beforeStreamingDuration);
  });
});
