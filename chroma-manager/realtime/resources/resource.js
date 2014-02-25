//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
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

var url = require('url'),
  uriTemplate = require('uritemplate'),
  moment = require('moment'),
  dotty = require('dotty'),
  _ = require('lodash');

var pendCount = 0;

/**
 * Creates a new Resource CLASS when called
 * @param {conf} conf
 * @param {request} request
 * @param {Object} logger
 * @param {Q} Q
 * @returns {Resource}
 */
module.exports = function resourceFactory(conf, request, logger, Q) {
  /*
   * The Base Resource
   * @name Resource
   * @constructor
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
    this.baseUrl = url.resolve(conf.apiUrl, path);

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
    params = params || {};

    return this.request.get(params);
  };

  /**
   * The default implementation for GETting metrics
   * Converts a sliding window duration in qs.unit, qs.size to qs.begin, qs.end
   * This could probably be mixed in instead.
   * @param {Object} params
   * @returns {Q.promise}
   */
  Resource.prototype.__httpGetMetrics = function __httpGetMetrics (params) {
    var end;

    var clonedParams = _.cloneDeep(params || {}),
      unit = dotty.get(clonedParams, 'qs.unit'),
      size = dotty.get(clonedParams, 'qs.size');

    if (size != null && unit != null) {
      end = moment().utc();

      dotty.put(clonedParams, 'qs.end', end.toISOString());
      dotty.put(clonedParams, 'qs.begin', end.subtract(unit, size).toISOString());
    }

    return this.requestFor({extraPath: 'metric'}).get(clonedParams);
  };

  /**
   * This creates a new default request with the option to expand a template.
   * Trailing slash is enforced and normalized.
   * @param {Object} [templateParams]
   * @returns {Object}
   */
  Resource.prototype.requestFor = function requestFor(templateParams) {
    var self = this;

    var expanded = uriTemplate
      .parse(this.baseUrl + '{/extraPath}{/id}')
      .expand(templateParams || {})
      .replace(/\/*$/, '/');

    var defaultRequest = request.defaults({
      jar: true,
      json: true,
      ca: conf.caFile,
      url: expanded,
      strictSSL: false,
      maxSockets: 25,
      forever: true,
      timeout: 120000 // 2 minutes
    });

    return {
      get: function (params) {
        var time = process.hrtime();

        pendCount += 1;

        return Q.ninvoke(defaultRequest, 'get', params)
          .spread(function (resp, body) {
            var diff = process.hrtime(time);
            var elapsed = parseInt(diff[1] / 1000000, 10); // divide by a million to get nano to milli

            self.log.debug('%s: %s (%d.%d seconds)', resp.statusCode, resp.request.href, diff[0], elapsed);

            pendCount -= 1;

            self.log.trace('pend count is: %d', pendCount);

            if (body)
              self.log.trace(body);

            if (resp.statusCode >= 400) {
              var message;

              try {
                message = JSON.stringify(body);
              } catch (e) {
                message = body;
              }

              throw new Error('status: ' + resp.statusCode + ', message: ' + message);
            }

            return resp;
          }, function () {
            pendCount -= 1;
          });
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