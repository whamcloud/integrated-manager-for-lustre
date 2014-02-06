'use strict';

var request = require('request'),
  querystring = require('querystring'),
  url = require('url');

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