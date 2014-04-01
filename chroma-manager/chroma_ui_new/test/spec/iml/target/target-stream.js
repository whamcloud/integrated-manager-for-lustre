describe('Target', function () {
  'use strict';

  beforeEach(module('target', {
    stream: jasmine.createSpy('stream')
  }));

  var replaceTransformer, stream;

  beforeEach(inject(function (_TargetStream_, _replaceTransformer_, _stream_) {
    replaceTransformer = _replaceTransformer_;
    stream = _stream_;
  }));

  it('should setup the stream', function () {
    expect(stream).toHaveBeenCalledOnceWith('target', 'httpGetList', {
      transformers: [replaceTransformer]
    });
  });
});