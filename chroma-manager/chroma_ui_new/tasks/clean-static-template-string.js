/* jshint node: true */

var util = require('util');

module.exports = function(grunt) {
  'use strict';

  grunt.registerTask(
    'cleanStaticTemplateString',
    'Cleans the Django {{STATIC_URL}} template string before building.',
    cleanStaticTemplateString
  );


  function cleanStaticTemplateString() {
    var _ = grunt.util._;

    /**
     * Remove Django {{STATIC_URL}} template string
     * @param {String} str
     * @returns {String}
     */
    function removeStatic(str) {
      return str.replace(/\{\{\s*STATIC_URL\s*\}\}/, '');
    }

    /**
     * Clones simple object structures.
     * @param {Object} obj A JSON serializable object.
     * @param {Function|Array} replacer If a function, transforms values and properties encountered while stringifying;
     *  if an array, specifies the set of properties included in objects in the final string.
     * @returns {Object}
     */
    function quickClone(obj, replacer) {
      return JSON.parse(JSON.stringify(obj, replacer));
    }

    //Get the configs we need to alter.
    var configs = ['uglify', 'cssmin', 'concat'].reduce(function (obj, config) {
      obj[config] = grunt.config(config);
      return obj;
    }, {});

    //Remove the template string from the object structure.
    var clean = quickClone(configs, function replacer(key, value) {
      if (_.isPlainObject(value)) {
        return Object.keys(value).reduce(function (obj, key) {
          obj[removeStatic(key)] = value[key];

          return obj;
        }, {});
      } else if (_.isString(value)) {
        value = removeStatic(value);
      }

      return value;
    });

    //Log the clean structure.
    grunt.log.subhead('Configuration cleaned. Now:');

    var keys = Object.keys(clean);
    keys.forEach(function (key) {
      grunt.log.subhead('  ' + key + ':')
        .writeln('  ' + util.inspect(clean[key], false, 4, true));
    });

    //Write the clean structure back to the config.
    keys.forEach(function (key) {
      grunt.config(key, clean[key]);
    });
  }
};

