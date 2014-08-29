/*jshint node: true*/
'use strict';

var configulator = require('configulator');
var path = require('path');
var configModule = require('../../config').wiretree;
var loggerModule = require('../../logger').wiretree;

describe('test logger', function() {
  var logger, newLogger, createLoggerParameter, bunyan, config, level;

  beforeEach(function() {
    process.env.NODE_ENV = 'test';
    config = configModule(configulator);
    level = 'debug';
    newLogger = {key: 'logger'};

    bunyan = {
      createLogger: jasmine.createSpy('createLogger').and.returnValue(newLogger),
      stdSerializers: {
        err: jasmine.createSpy('err')
      }
    };

    createLoggerParameter = {
      name: 'stubdaddy',
      serializers: {
        err: bunyan.stdSerializers.err
      },
      streams: [
        {
          type: 'file',
          level: 'debug',
          path: 'stubdaddy.log'
        }
      ]
    };

    logger = loggerModule(bunyan, path, config);
  });

  it('should call logger with appropriate params', function() {
    expect(bunyan.createLogger).toHaveBeenCalledWith(createLoggerParameter);
  });

  it('should return the logger instance', function() {
    expect(logger).toEqual(newLogger);
  });
});
