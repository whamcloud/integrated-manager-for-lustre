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


'use strict';

var url = require('url'),
  uriTemplate = require('uritemplate'),
  moment = require('moment'),
  dotty = require('dotty'),
  _ = require('lodash');

module.exports = function resourceFactory(conf, request, logger) {
  /*
   * The Base Resource
   * @constructor
   */
  function Resource (path) {
    if (!path)
      throw new Error('path not provided to resource');

    this.log = logger.child({resource: this.constructor.name});
    this.baseUrl = url.resolve(conf.apiUrl, path);
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
   * @param {Function} cb
   * @private
   */
  Resource.prototype.__httpGetList = function __httpGetList(params, cb) {
    params = params || {};

    this.request.get(params, this.createGenericGetHandler(cb, params));
  };

  /**
   * The default implementation for GETting metrics
   * Converts a sliding window duration in qs.unit, qs.size to qs.begin, qs.end
   * This could probably be mixed in instead.
   * @param {Object} params
   * @param {Function} cb
   */
  Resource.prototype.__httpGetMetrics = function __httpGetMetrics (params, cb) {
    var end;

    var clonedParams = _.cloneDeep(params || {}),
      unit = dotty.get(clonedParams, 'qs.unit'),
      size = dotty.get(clonedParams, 'qs.size');

    if (size != null && unit != null) {
      end = moment().utc();

      dotty.put(clonedParams, 'qs.end', end.toISOString());
      dotty.put(clonedParams, 'qs.begin', end.subtract(unit, size).toISOString());
    }

    this.requestFor({extraPath: 'metric'}).get(clonedParams, this.createGenericGetHandler(cb, params));
  };

  /**
   * This creates a new default request with the option to expand a template.
   * Trailing slash is enforced and normalized.
   * @param {Object} [templateParams]
   * @returns {Request}
   */
  Resource.prototype.requestFor = function requestFor(templateParams) {
    var expanded = uriTemplate
      .parse(this.baseUrl + '{/extraPath}{/id}')
      .expand(templateParams || {})
      .replace(/\/*$/, '/');

    return request.defaults({
      jar: true,
      json: true,
      ca: conf.caFile,
      url: expanded,
      strictSSL: false
    });
  };

  /**
   * A higher order function that returns a GET response handler.
   * @param {Function} cb
   * @returns {Function}
   */
  Resource.prototype.createGenericGetHandler = function createGenericGetHandler(cb, params) {
    return function genericGetHandler(err, resp, body) {
      if (err) {
        cb({error: err});
      } else if (resp.statusCode >= 400) {
        cb({status: resp.statusCode, error: body });
      } else {
        cb(null, resp, body, params);
      }
    };
  };


  /**
   * Gets the subclass resource methods based on naming conventions.
   */
  Resource.prototype.getHttpMethods = function getHttpMethods () {
    var regExp = new RegExp('^http.+$'),
      arr = [];

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