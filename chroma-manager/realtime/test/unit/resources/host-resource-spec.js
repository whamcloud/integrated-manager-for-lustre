'use strict';

var sinon = require('sinon'),
  hostResourceFactory = require('../../../resources/host-resource');

require('jasmine-sinon');

describe('Host resource', function () {
  var Resource, HostResource, hostResource;

  beforeEach(function () {
    Resource = sinon.spy();

    sinon.stub(Resource, 'call');

    HostResource = hostResourceFactory(Resource);

    hostResource = new HostResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledWithExactly(hostResource, 'host');
  });

  it('should allow GetList and GetMetrics', function () {
    expect(hostResource.defaults).toEqual(['GetList', 'GetMetrics']);
  });
});
