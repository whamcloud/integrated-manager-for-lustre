'use strict';

/**
 * Waits for promise to resolve before calling done.
 * @param {String} desc
 * @param {Function} func
 * @returns {Object}
 */
global.pit = function pit (desc, func) {
  return jasmine.getEnv().it(desc, getWaiter(func));
};

/**
 * Skips this spec
 * @param {String} desc
 * @param {Function} func
 * @returns {Object}
 */
global.xpit = function xpit (desc, func) {
  return jasmine.getEnv().xit(desc, getWaiter(func));
};

/**
 * Puts this spec into an inclusive list
 * @param {String} desc
 * @param {Function} func
 * @returns {Object}
 */
global.ipit = function ipit (desc, func) {
  return global.iit(desc, getWaiter(func));
};

/**
 * HOF that waits for the promise to finish.
 * @param {Function} func
 * @returns {Function}
 */
function getWaiter (func) {
  return function waiter (done) {
    func().done(done);
  };
}
