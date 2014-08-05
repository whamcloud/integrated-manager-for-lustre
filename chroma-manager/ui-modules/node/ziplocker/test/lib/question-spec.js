'use strict';

var questionModule = require('../../lib/question').wiretree;
var Promise = require('promise');

describe('question module', function () {
  var question, readline, readlineInterface;

  beforeEach(function () {
    readlineInterface = {
      question: jasmine.createSpy('question'),
      close: jasmine.createSpy('close')
    };

    readline = {
      createInterface: jasmine.createSpy('createInterface')
        .and.returnValue(readlineInterface)
    };

    question = questionModule(readline, Promise);
  });

  it('should return an object', function () {
    expect(question).toEqual(jasmine.any(Object));
  });

  describe('ask', function () {
    it('should have an ask property', function () {
      expect(question.ask).toEqual(jasmine.any(Function));
    });

    it('should return a promise', function () {
      expect(question.ask('foo?')).toEqual(jasmine.any(Promise));
    });

    it('should create a readline interface', function () {
      question.ask('foo?');

      expect(readline.createInterface).toHaveBeenCalledWith({
        input: process.stdin,
        output: process.stdout
      });
    });

    pit('should reject if the question is not a string', function () {
      var noQuestion = question.ask(10);

      return noQuestion
        .catch(function (error) {
          expect(error).toEqual(new Error('question must be a non-empty string.'));
        });
    });

    pit('should reject if the question is empty', function () {
      var noQuestion = question.ask('');

      return noQuestion
        .catch(function (error) {
          expect(error).toEqual(new Error('question must be a non-empty string.'));
        });
    });

    describe('asking a question', function () {
      var waitForResponse;

      beforeEach(function () {
        waitForResponse = question.ask('How are you?');
      });

      it('should ask the question', function () {
        expect(readlineInterface.question).toHaveBeenCalledWith('How are you?', jasmine.any(Function));
      });

      pit('should resolve with the answer', function () {
        readlineInterface.question.calls.mostRecent().args[1]('good');

        return waitForResponse.then(function (answer) {
          expect(answer).toEqual('good');
        });
      });

      pit('should close the readline interface', function () {
        readlineInterface.question.calls.mostRecent().args[1]('good');

        return waitForResponse.then(function () {
          expect(readlineInterface.close).toHaveBeenCalled();
        });
      });
    });
  });

  describe('yes or no', function () {

    var waitForResponse;

    beforeEach(function () {
      waitForResponse = question.yesOrNo('Sushi?');
    });

    it('should have a yesOrNo property', function () {
      expect(question.yesOrNo).toEqual(jasmine.any(Function));
    });

    it('should return a promise', function () {
      expect(waitForResponse).toEqual(jasmine.any(Promise));
    });

    it('should ask the question', function () {
      expect(readlineInterface.question).toHaveBeenCalledWith('Sushi?', jasmine.any(Function));
    });

    ['yes', 'y', 'yes ', ' y ', 'Yes', 'Y'].forEach(function (answer) {
      pit('should return true for ' + answer, function () {
        var calls = readlineInterface.question.calls;

        calls.first().args[1](answer);

        return waitForResponse.then(function (answer) {
          expect(answer).toBe(true);
        });
      });
    });

    ['no', 'n', ' no ', ' n', 'No', 'N'].forEach(function (answer) {
      pit('should return false for ' + answer, function () {
        var calls = readlineInterface.question.calls;

        calls.first().args[1](answer);
        return waitForResponse.then(function (answer) {
          expect(answer).toBe(false);
        });
      });
    });
  });
});
