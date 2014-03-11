'use strict';

var commandResourceFactory = require('../../../resources/command-resource');

describe('Command resource', function () {
  var Resource, CommandResource, commandResource;

  beforeEach(function () {
    Resource = function () {};

    spyOn(Resource, 'call');

    CommandResource = commandResourceFactory(Resource);

    commandResource = new CommandResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledOnceWith(commandResource, 'command');
  });

  it('should allow GetList', function () {
    expect(commandResource.defaults).toEqual(['GetList']);
  });
});