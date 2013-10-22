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


(function () {
  'use strict';

  /**
   * We need our custom method because encodeURIComponent is too aggressive and doesn't follow
   * http://www.ietf.org/rfc/rfc3986.txt with regards to the character set (pchar) allowed in path
   * segments:
   *    segment       = *pchar
   *    pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
   *    pct-encoded   = "%" HEXDIG HEXDIG
   *    unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
   *    sub-delims    = "!" / "$" / "&" / "'" / "(" / ")"
   *                     / "*" / "+" / "," / ";" / "="
   */
  function encodeUriSegment(val) {
    return encodeUriQuery(val, true)
      .replace(/%26/gi, '&')
      .replace(/%3D/gi, '=')
      .replace(/%2B/gi, '+');
  }

  /**
   * This method is intended for encoding *key* or *value* parts of query component. We need a custom
   * method because encodeURIComponent is too aggressive and encodes stuff that doesn't have to be
   * encoded per http://tools.ietf.org/html/rfc3986:
   *    query       = *( pchar / "/" / "?" )
   *    pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
   *    unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
   *    pct-encoded   = "%" HEXDIG HEXDIG
   *    sub-delims    = "!" / "$" / "&" / "'" / "(" / ")"
   *                     / "*" / "+" / "," / ";" / "="
   */
  function encodeUriQuery(val, pctEncodeSpaces) {
    return encodeURIComponent(val)
      .replace(/%40/gi, '@')
      .replace(/%3A/gi, ':')
      .replace(/%24/g, '$')
      .replace(/%2C/gi, ',')
      .replace(/%20/g, (pctEncodeSpaces ? '%20' : '+'));
  }

  /**
   * @constructor
   * @param {String} template
   * @param {function} formatBaseUrl
   */
  function Route (template, formatBaseUrl) {
    this.template = template;
    this.formatBaseUrl = formatBaseUrl || angular.identity;
    this.defaults = {};
    this.urlParams = {};
  }

  /**
   *
   * @param config
   * @param actionUrl
   * @param params
   */
  Route.prototype.setUrlParams = function setUrlParams(config, params, actionUrl) {
    var url = actionUrl || this.template;
    var urlParams = this.urlParams = {};

    url.split(/\W/).forEach(function (param) {
      var matchesParam = new RegExp('(^|[^\\\\]):%s(\\W|$)'.sprintf(param));

      if (param && (matchesParam.test(url))) {
        this.urlParams[param] = true;
      }
    }, this);

    url = url.replace(/\\:/g, ':');

    Object.keys(urlParams).forEach(function (urlParam) {
      var val = params.hasOwnProperty(urlParam) ? params[urlParam] : this.defaults[urlParam];

      if (angular.isDefined(val) && val !== null) {
        var encodedVal = encodeUriSegment(val);
        var foundParams = new RegExp(':%s(\\W|$)'.sprintf(urlParam), 'g');

        url = url.replace(foundParams, encodedVal + '$1');
      } else {
        var missingParams = new RegExp('(\/?):%s(\\W|$)'.sprintf(urlParam), 'g');

        url = url.replace(missingParams, function (match, leadingSlashes, tail) {
          if (tail.charAt(0) === '/') {
            return tail;
          } else {
            return leadingSlashes + tail;
          }
        });
      }
    }, this);

    config.url = url
      // strip trailing slashes and set the url
      .replace(/\/+$/, '')
      // then replace collapse `/.` if found in the last URL path segment before the query
      // E.g. `http://url.com/id./format?q=x` becomes `http://url.com/id.format?q=x`
      .replace(/\/\.(?=\w+($|\?))/, '.')
      // replace escaped `/\.` with `/.`
      .replace(/\/\\\./, '/.');

    config.url = this.formatBaseUrl(config.url);

    // set params - delegate param encoding to $http
    _.forEach(params, function (value, key) {
      if (!urlParams[key]) {
        config.params = config.params || {};
        config.params[key] = value;
      }
    }, this);
  };

  angular.module('resourceful').factory('route', [function () {
    return function getRouter(template, formatBaseUrl) {
      return new Route(template, formatBaseUrl);
    };
  }]);
}());
