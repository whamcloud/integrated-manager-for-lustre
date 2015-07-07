describe('file system stream', function () {
  'use strict';

  var FileSystemStream, stream, fileSystemStreamModelTransformer, replaceTransformer;

  beforeEach(module('fileSystem'));

  mock.beforeEach('BASE',
    function createMocks() {
      stream = jasmine.createSpy('stream').andCallFake(function () {
        return function streamInstance() {};
      });

      fileSystemStreamModelTransformer = jasmine.createSpy('fileSystemStreamModelTransformer');
      replaceTransformer = jasmine.createSpy('replaceTransformer');

      return [
        { name: 'stream', value: stream },
        { name: 'fileSystemStreamModelTransformer', value: fileSystemStreamModelTransformer },
        { name: 'replaceTransformer', value: replaceTransformer }
      ];
    }
  );

  beforeEach(inject(function (_FileSystemStream_) {
    FileSystemStream = _FileSystemStream_;
  }));

  it('should configure the stream', function () {
    var expectedConfig = {
      transformers: [fileSystemStreamModelTransformer, replaceTransformer]
    };

    expect(stream).toHaveBeenCalledOnceWith('filesystem', 'httpGetList', expectedConfig);
  });
});
