describe('Host', function () {
  'use strict';

  beforeEach(module('host', {
    stream: jasmine.createSpy('stream')
  }));

  var replaceTransformer, stream;

  beforeEach(inject(function (_HostStream_, _replaceTransformer_, _stream_) {
    replaceTransformer = _replaceTransformer_;
    stream = _stream_;
  }));

  it('should setup the stream', function () {
    expect(stream).toHaveBeenCalledOnceWith('host', 'httpGetList', {
      transformers: [replaceTransformer]
    });
  });
});