'use strict';

module.exports = function clone (val) {
  return JSON.parse(JSON.stringify(val));
};
