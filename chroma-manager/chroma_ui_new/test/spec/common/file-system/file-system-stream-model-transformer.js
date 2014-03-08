describe('file system stream model transformer', function () {
  'use strict';

  var FileSystemStreamModel, fileSystemStreamModel, fileSystemStreamModelTransformer, resp;

  beforeEach(module('fileSystem'));

  mock.beforeEach(function createMock() {
    fileSystemStreamModel = {};

    FileSystemStreamModel = jasmine.createSpy('FileSystemStreamModel').andCallFake(function () {
      return fileSystemStreamModel;
    });

    return {
      name: 'FileSystemStreamModel',
      value: FileSystemStreamModel
    };
  });

  beforeEach(inject(function (_fileSystemStreamModelTransformer_) {
    fileSystemStreamModelTransformer = _fileSystemStreamModelTransformer_;

    resp = {
      body: {
        objects: []
      }
    };
  }));

  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      fileSystemStreamModelTransformer({});
    }

    expect(shouldThrow).toThrow('fileSystemStreamModelTransformer expects resp.body to be an object!');
  });

  describe('enhancing items', function () {
    var fakeRecord, result;

    beforeEach(function () {
      fakeRecord = {
        fakeProperty: 'fakeValue'
      };

      resp.body.objects.push(fakeRecord);

      result = fileSystemStreamModelTransformer(resp);
    });

    it('should convert objects to FileSystemStreamModels', function () {
      expect(FileSystemStreamModel).toHaveBeenCalledOnceWith(fakeRecord);
    });

    it('should replace the response body with the vivified objects', function () {
      expect(resp.body.objects[0]).toBe(fileSystemStreamModel);
    });

    it('should resolve with the resp', function () {
      expect(result).toBe(resp);
    });
  });
});