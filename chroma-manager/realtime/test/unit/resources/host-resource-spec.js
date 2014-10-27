'use strict';

var hostResourceFactory = require('../../../resources/host-resource').wiretree;

describe('Host resource', function () {
  var Resource, HostResource, hostResource;

  beforeEach(function () {
    Resource = jasmine.createSpy('Resource');

    spyOn(Resource, 'call');

    HostResource = hostResourceFactory(Resource);

    hostResource = new HostResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledOnceWith(hostResource, 'host');
  });

  it('should allow GetList and GetMetrics', function () {
    expect(hostResource.defaults).toEqual(['GetList', 'GetMetrics']);
  });
});
