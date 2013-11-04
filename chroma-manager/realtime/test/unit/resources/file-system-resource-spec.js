'use strict';

var sinon = require('sinon'),
  fileSystemResourceFactory = require('../../../resources/file-system-resource');

require('jasmine-sinon');

describe('file system resource', function () {
  var Resource, FileSystemResource, fileSystemResource;

  beforeEach(function () {
    Resource = sinon.spy();

    sinon.stub(Resource, 'call');

    FileSystemResource = fileSystemResourceFactory(Resource);

    fileSystemResource = new FileSystemResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledWithExactly(fileSystemResource, 'filesystem');
  });

  it('should allow GetList', function () {
    expect(fileSystemResource.defaults).toEqual(['GetList']);
  });
});