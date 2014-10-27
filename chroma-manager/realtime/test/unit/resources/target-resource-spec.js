'use strict';

var targetResourceFactory = require('../../../resources/target-resource').wiretree;

describe('Host resource', function () {
  var Resource, TargetResource, targetResource;

  beforeEach(function () {
    Resource = jasmine.createSpy('Resource');

    spyOn(Resource, 'call');

    TargetResource = targetResourceFactory(Resource);

    targetResource = new TargetResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledOnceWith(targetResource, 'target');
  });

  it('should allow GetMetrics', function () {
    expect(targetResource.defaults).toEqual(['GetList', 'GetMetrics']);
  });
});
