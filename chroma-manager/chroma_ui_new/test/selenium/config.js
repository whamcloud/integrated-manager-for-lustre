(function () {
  'use strict';

  var util = require('util'),
    _ = require('lodash-contrib'),
    regexp = /^config=/;

  var file = process.argv.reduce(function (file, arg) {
    if (regexp.test(arg)) file = arg.replace(regexp, '');

    return file;
  }, './sample-config');

  var config = require(file);

  // Walks the config adding element selection methods to any collections found.
  _.walk(config, function (val, key) {
    if (!Array.isArray(val)) return;

    val.get = function get(predicate) {
      var item = val.filter(predicate);

      if (!item.length) throw new Error(util.format('No matching %s found!', key));

      return item.pop();
    };

    val.getFirst = function getFirst() {
      return this.get(function (item, index) { return index === 0; });
    };
  });

  module.exports = config;
}());
