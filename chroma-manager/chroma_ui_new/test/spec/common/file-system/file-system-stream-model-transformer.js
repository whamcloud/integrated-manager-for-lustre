describe('file system stream model transformer', function () {
  'use strict';

  /**
   * Empty constructor used to assert instance.
   * @constructor
   */
  function FileSystemStreamModel () {}

  beforeEach(module('fileSystem', {
    FileSystemStreamModel: FileSystemStreamModel
  }));

  var fileSystemStreamModelTransformer;

  beforeEach(inject(function (_fileSystemStreamModelTransformer_) {
    fileSystemStreamModelTransformer = _fileSystemStreamModelTransformer_;
  }));

  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      fileSystemStreamModelTransformer({});
    }

    expect(shouldThrow).toThrow('fileSystemStreamModelTransformer expects resp.body to be an object!');
  });

  describe('enhancing items', function () {
    var result, resp;

    beforeEach(function () {
      resp = {
        body: {
          objects: [{
            fakeProperty: 'fakeValue'
          }]
        }
      };

      result = fileSystemStreamModelTransformer(resp);
    });

    it('should replace the response body with the vivified objects', function () {
      expect(resp.body.objects[0]).toEqual(jasmine.any(FileSystemStreamModel));
    });

    it('should resolve with the resp', function () {
      expect(result).toBe(resp);
    });
  });

  describe('enhancing an item', function () {
    var resp, result;

    beforeEach(function () {
      resp = {
        body: {
          fakeProperty: 'fakeValue'
        }
      };

      result = fileSystemStreamModelTransformer(resp);
    });

    it('should replace the response body with a vivified object', function () {
      expect(resp.body).toEqual(jasmine.any(FileSystemStreamModel));
    });
  });
});
