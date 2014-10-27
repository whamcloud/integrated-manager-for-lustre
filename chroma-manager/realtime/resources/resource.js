//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


/** @module resources/resource */

'use strict';

var uriTemplate = require('uritemplate');

/**
 * Creates a new Resource CLASS when called
 * @param {request} request
 * @param {Object} logger
 * @param {Object} _
 * @returns {Resource}
 */
exports.wiretree = function resourceFactory (request, logger, _) {
  /*
   * The Base Resource
   * @name Resource
   * @constructor
   * @param {String} path
   */
  function Resource (path) {
    if (!path)
      throw new Error('path not provided to resource');

    /**
     * @methodOf Resource
     * @type {Object}
     */
    this.log = logger.child({resource: this.constructor.name});

    /**
     * @methodOf Resource
     * @type {string}
     */
    this.path = path;

    /**
     * @methodOf Resource
     * @type {Object}
     */
    this.request = this.requestFor();

    //Look for defaults.
    if (Array.isArray(this.defaults))
      this.defaults.forEach(function (method) {
        this['http' + method] = this['__http' + method];
      }, this);
  }

  /**
   * The default implementation of a GET request.
   * If a subclass lists this as a default method it will be used without the leading __.
   * This could probably be mixed in instead.
   * @param {Object} params
   * @returns {Q.promise}
   * @private
   */
  Resource.prototype.__httpGetList = function __httpGetList(params) {
    params = _.cloneDeep(params || {});

    if (params.id) {
      var id = {id: params.id};
      delete params.id;

      return this.requestFor(id).get(params);
    } else {
      return this.request.get(params);
    }
  };

  /**
   * The default implementation for GETting metrics
   * This could probably be mixed in instead.
   * @param {Object} params
   * @returns {Q.promise}
   */
  Resource.prototype.__httpGetMetrics = function __httpGetMetrics (params) {
    params = _.cloneDeep(params || {});

    var requestParams = {
      extraPath: 'metric'
    };

    if (params.id) {
      requestParams.id = params.id;
      delete params.id;
    }

    return this.requestFor(requestParams).get(params);
  };

  /**
   * This creates a new default request with the option to expand a template.
   * Trailing slash is enforced and normalized.
   * @param {Object} [templateParams]
   * @returns {Object}
   */
  Resource.prototype.requestFor = function requestFor(templateParams) {
    var expanded = uriTemplate
      .parse(this.path + '{/id}{/extraPath}')
      .expand(templateParams || {});

    return {
      get: function (options) {
        return request.get(expanded, options);
      }
    };
  };

  /**
   * Gets the subclass resource methods based on naming conventions.
   */
  Resource.prototype.getHttpMethods = function getHttpMethods () {
    var regExp = new RegExp('^http.+$'),
      arr = [];

    /*jshint forin: false */
    for (var key in this) {
      var result = regExp.exec(key);

      if (result != null) {
        var match = result.shift();
        arr.push(match);
      }
    }

    return arr;
  };

  return Resource;
};
