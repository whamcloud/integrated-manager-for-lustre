(function () {
  'use strict';

  var util = require('util');
  var _ = require('lodash-contrib');
  var argv = require('optimist').argv;
  var file = argv.config || './sample-config';
  var uiPath = argv.uiPath || 'ui/';

  var config = require(file);

  // Walks the config adding element selection methods to any collections found.
  _.walk.preorder(config, function (val, key) {
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

  config.uiPath = uiPath;

  module.exports = config;
}());
