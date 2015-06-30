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

var viewRouter = require('../view-router');
var templates = require('../lib/templates');
var requestStream = require('../lib/request-stream');
var renderRequestError = require('../lib/render-request-error');

var indexTemplate = templates['new/index.html'];

module.exports = function loginRoute () {
  viewRouter.route('/ui/login')
  /**
   * If the user is already authenticated and the eula is accepted, redirects to index page.
   * If the user is already authenticated and the eula is not accepted, logs the user out.
   * @param {Object} req
   * @param {Object} res
   * @param {Object} data
   * @param {Function} next
   */
    .get(function checkEula (req, res, data, next) {
      var session = data.cache.session;

      if (!session.user)
        return goToNext();

      if (session.user.eula_state === 'pass')
        return res.redirect('/ui/');
      else
        requestStream('/session', {
          method: 'delete',
          headers: { cookie: data.cacheCookie }
        })
          .stopOnError(renderRequestError(res, function writeDescription (err) {
            return 'Exception rendering resources: ' + err.stack;
          }))
          .each(goToNext);

      function goToNext () {
        next(req, res, data.cache);
      }

    })
  /**
   * Renders the login page.
   * @param {Object} req
   * @param {Object} res
   * @param {Object} cache
   * @param {Function} next
   */
    .get(function renderLogin (req, res, cache, next) {
      res.clientRes.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.clientRes.statusCode = 200;

      var rendered = indexTemplate({
        title: 'Login',
        cache: cache
      });

      res.clientRes.end(rendered);

      next(req, res);
    });
};
