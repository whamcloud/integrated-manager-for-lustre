'use strict';

var execThenModule = require('../../lib/exec-then').wiretree;
var Promise = require('promise');

describe('exec then', function () {
  var childProcess, execThen;

  beforeEach(function () {
    childProcess = {
      exec: jasmine.createSpy('exec')
    };

    execThen = execThenModule(childProcess, Promise);
  });

  it('should return a promise', function () {
    expect(execThen('ls')).toEqual(jasmine.any(Promise));
  });

  pit('should resolve on success', function () {
    childProcess.exec.and.callFake(function (command, cb) {
      cb(null, 'ookkay', 'error');
    });

    return execThen('ls -ltr').then(function (outputs) {
      expect(outputs).toEqual(['ookkay', 'error']);
    });
  });

  pit('should reject on error', function () {
    childProcess.exec.and.callFake(function (command, cb) {
      cb(new Error('Your hard drive died!'));
    });

    return execThen('ls').catch(function (error) {
      expect(error).toEqual(new Error('Your hard drive died!'));
    });
  });

});
