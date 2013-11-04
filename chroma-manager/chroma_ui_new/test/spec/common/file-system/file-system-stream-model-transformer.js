describe('file system stream model transformer', function () {
  'use strict';

  var $rootScope, FileSystemStreamModel, fileSystemStreamModel, fileSystemStreamModelTransformer, deferred, resp;

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

  beforeEach(inject(function ($q, _$rootScope_, _fileSystemStreamModelTransformer_) {
    fileSystemStreamModelTransformer = _fileSystemStreamModelTransformer_;

    $rootScope = _$rootScope_;
    deferred = $q.defer();

    resp = {
      body: {
        objects: []
      }
    };
  }));

  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      fileSystemStreamModelTransformer({}, deferred);
    }

    expect(shouldThrow).toThrow('fileSystemStreamModelTransformer expects resp.body to be an object!');
  });

  describe('enhancing items', function () {
    var fakeRecord;

    beforeEach(function () {
      fakeRecord = {
        fakeProperty: 'fakeValue'
      };

      resp.body.objects.push(fakeRecord);

      fileSystemStreamModelTransformer(resp, deferred);
    });

    it('should convert objects to FileSystemStreamModels', function () {
      expect(FileSystemStreamModel).toHaveBeenCalledOnceWith(fakeRecord);
    });

    it('should replace the response body with the vivified objects', function () {
      expect(resp.body.objects[0]).toBe(fileSystemStreamModel);
    });

    it('should resolve with the resp', function () {
      deferred.promise.then(function (out) {
        expect(out).toBe(resp);
      });

      $rootScope.$digest();
    });
  });
});