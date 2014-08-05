'use strict';

var logModule = require('../../lib/log').wiretree;

describe('Log', function () {
  var log, console, logDiffObjects, question, chalk;

  beforeEach(function () {
    console = {
      log: jasmine.createSpy('log')
    };

    chalk = {
      blue: jasmine.createSpy('blue').and.callFake(function (str) {return str;})
    };

    logDiffObjects = {};

    question = {};

    log = logModule(console, chalk, logDiffObjects, question);
  });

  it('should return an object', function () {
    expect(log).toEqual({
      write: jasmine.any(Function),
      diffObjects: logDiffObjects,
      question: question
    });
  });

  it('should extend chalk', function () {
    expect(Object.getPrototypeOf(log)).toBe(chalk);
  });

  describe('writing a message', function () {
    beforeEach(function () {
      log.write('hello');
    });

    it('should prepend with ziplock', function () {
      expect(chalk.blue).toHaveBeenCalledWith('ziplock');
    });

    it('should write a message', function () {
      expect(console.log).toHaveBeenCalledWith('ziplock', 'hello');
    });
  });
});
