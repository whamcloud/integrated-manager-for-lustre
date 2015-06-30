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

var λ = require('highland');
var templates = require('./templates');
var conf = require('../conf');

var handler = λ.curry(function indexHandler (template, req, res, data, next) {
  var session = data.cache.session;

  if (!session.user && !conf.allowAnonymousRead)
    return res.redirect('/ui/login/');

  res.clientRes.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.clientRes.statusCode = 200;

  var rendered = template({
    title: '',
    cache: data.cache
  });

  res.clientRes.end(rendered);

  next(req, res);
});

var newTemplate = templates['new/index.html'];
var oldTemplate = templates['base.html'];

module.exports = {
  oldHandler: handler(oldTemplate),
  newHandler: handler(newTemplate)
};
