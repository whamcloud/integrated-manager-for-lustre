'use strict';

var sinon = require('sinon'),
  targetResourceFactory = require('../../../resources/target-resource');

require('jasmine-sinon');

describe('Host resource', function () {
  var Resource, TargetResource, targetResource;

  beforeEach(function () {
    Resource = sinon.spy();

    sinon.stub(Resource, 'call');

    TargetResource = targetResourceFactory(Resource);

    targetResource = new TargetResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledWithExactly(targetResource, 'target');
  });

  it('should allow GetMetrics', function () {
    expect(targetResource.defaults).toEqual(['GetList', 'GetMetrics']);
  });
});