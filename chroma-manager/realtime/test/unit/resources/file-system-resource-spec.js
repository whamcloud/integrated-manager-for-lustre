'use strict';

var fileSystemResourceFactory = require('../../../resources/file-system-resource').wiretree;

describe('file system resource', function () {
  var Resource, FileSystemResource, fileSystemResource;

  beforeEach(function () {
    Resource = jasmine.createSpy('Resource');

    spyOn(Resource, 'call');

    FileSystemResource = fileSystemResourceFactory(Resource);

    fileSystemResource = new FileSystemResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledOnceWith(fileSystemResource, 'filesystem');
  });

  it('should allow GetList', function () {
    expect(fileSystemResource.defaults).toEqual(['GetList']);
  });
});
