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


'use strict';

var request = require('request');
var querystring = require('querystring');
var url = require('url');

/**
 * Override the default qs to use querystring instead.
 * @param q
 * @param clobber
 * @returns {request.Request}
 */
request.Request.prototype.qs = function (q, clobber) {
  //@Fixme: This is *brittle*, we are stuck until either:
  // 1) Something happens on https://github.com/mikeal/request/issues/644
  // 2) We upgrade to tastypie: 0.9.12: https://github.com/toastdriven/django-tastypie/pull/388
  var base;
  if (!clobber && this.uri.query)
    base = querystring.parse(this.uri.query);
  else base = {};

  for (var i in q) {
    base[i] = q[i];
  }

  if (querystring.stringify(base) === '')
    return this;

  this.uri = url.parse(this.uri.href.split('?')[0] + '?' + querystring.stringify(base));
  this.url = this.uri;
  this.path = this.uri.path;

  return this;
};

module.exports = request;
