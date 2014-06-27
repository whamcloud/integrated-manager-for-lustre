/*jshint node: true*/
'use strict';
var configModule = require('../../config').wiretree;

describe('test returning config from configulator', function() {

  var config, envConfig, configulator;
  beforeEach(function() {
    envConfig = {
      key: 'value'
    };

    configulator = jasmine.createSpy('configulator').and.returnValue(envConfig);
    config = configModule(configulator);
  });

  it('should call configulator with config object', function() {
    expect(configulator).toHaveBeenCalledWith(jasmine.any(Object));
  });

  it('should return the environment config', function() {
    expect(config).toEqual(envConfig);
  });
});
