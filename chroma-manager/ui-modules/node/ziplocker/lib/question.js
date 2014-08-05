'use strict';

/**
 * Abstraction for asking a user a question over the command line.
 * @param {readline} readline
 * @param {Promise} Promise
 * @returns {{ask: Function, yesOrNo: Function}}
 */
exports.wiretree = function questionModule (readline, Promise) {

  return {
    ask: ask,
    yesOrNo: yesOrNo
  };

  /**
   * Asks a question over stdout.
   * Returns a promise representing it's answer.
   * @param {String} question
   * @returns {Promise}
   */
  function ask (question) {
    var rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    return new Promise(function handlePromise (resolve, reject) {
      if (typeof question !== 'string' || question.length === 0)
        reject(new Error('question must be a non-empty string.'));

      rl.question(question, function handleAnswer (answer) {
        rl.close();
        resolve(answer);
      });
    });
  }

  /**
   * Given a question, asks it over stdout until
   * a yes or no response is given.
   * @param {String} question
   * @returns {Promise}
   */
  function yesOrNo (question) {
    var affirmative = ['yes', 'y'];
    var negative = ['no', 'n'];

    return (function askThenCheck () {
      return ask(question)
        .then(function checkAnswer (answer) {
          var answerIterator = shouldAcceptAnswer(answer);

          var accepted = affirmative.some(answerIterator);
          var rejected = !accepted && negative.some(answerIterator);

          if (accepted)
            return Promise.resolve(true);
          else if (rejected)
            return Promise.resolve(false);
          else
            return askThenCheck();
        });
    }());

    /**
     * HOF. Is the answer acceptable.
     * @param {String} answer
     * @returns {Function}
     */
    function shouldAcceptAnswer (answer) {
      return function (acceptableAnswer) {
        return acceptableAnswer.toLowerCase().trim() === answer.toLowerCase().trim();
      };
    }
  }
};
