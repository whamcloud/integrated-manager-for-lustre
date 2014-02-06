'use strict';

var alertResourceFactory = require('../../../resources/alert-resource');

describe('Alert resource', function () {
  var Resource, AlertResource, alertResource;

  beforeEach(function () {
    Resource = function () {};

    spyOn(Resource, 'call');

    AlertResource = alertResourceFactory(Resource);

    alertResource = new AlertResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledOnceWith(alertResource, 'alert');
  });

  it('should allow GetList', function () {
    expect(alertResource.defaults).toEqual(['GetList']);
  });
});