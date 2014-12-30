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
 * Waits for promise to resolve before calling done.
 * @param {Function} func
 * @returns {Object}
 */
global.pbeforeEach = function beforeEach (func) {
  return global.beforeEach(getWaiter(func));
};

/**
 * Waits for promise to resolve before calling done.
 * @param {Function} func
 * @returns {Object}
 */
global.pafterEach = function beforeEach (func) {
  return global.afterEach(getWaiter(func));
};

/**
 * HOF. Allows equal expectation to take on a more
 * fluent interface.
 * @param {*} expected
 * @returns {Function}
 */
global.expectToEqual = function expectToEqualWrap (expected) {
  return function expectToEqual (val) {
    expect(val).toEqual(expected);
  };
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
