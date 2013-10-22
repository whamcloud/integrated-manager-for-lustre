(function () {
  'use strict';

  /**
   * Given an array of promises, returns a promise that will be resolved or rejected with the first promise in the list
   * that does so.
   * @param {array} promises
   * @returns {webdriver.promise}
   */
  exports.any = function any(promises) {
    var d = protractor.promise.defer();

    if (!Array.isArray(promises)) throw new Error('Call to promise.any expects an array of values!');

    promises.forEach(function (promise) { promise.then(d.fulfill, d.reject); });

    return d.promise;
  };
}());
