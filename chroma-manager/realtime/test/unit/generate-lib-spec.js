'use strict';

var generateLib = require('../../generate-lib').wiretree;

describe('generate lib', function () {
  var primus, lib;

  beforeEach(function () {
    primus = {
      library: jasmine.createSpy('library').andReturn('lib'),
      end: jasmine.createSpy('end')
    };

    lib = generateLib(primus);
  });

  it('should invoke the library method', function () {
    expect(primus.library).toHaveBeenCalledOnce();
  });

  it('should end the instance', function () {
    expect(primus.end).toHaveBeenCalledOnce();
  });

  it('should return the lib', function () {
    expect(lib).toEqual('lib');
  });
});
