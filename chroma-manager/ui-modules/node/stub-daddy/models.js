/*jshint node: true*/
'use strict';

exports.wiretree = function models(config, url, querystring) {

  /**
   * A RequestEntry model which represents a request, its response, and how many times it can be called before it is
   * removed (expires). If expires is 0 then it can be called as many times as you want but any other number will mean
   * that it uses a counter.
   * @param {Object} request
   * @param {Object} response
   * @param {Number} expires - A number >= 0
   * @constructor
   */
  function RequestEntry(request, response, expires) {
    this.request = request;
    this.response = response;
    this.expires = expires;
    this.remainingCalls = (expires > 0) ? expires : 1;

  }

  /**
   * Anytime a request is made we must update the call count to indicate how many
   * calls remain.
   */
  RequestEntry.prototype.updateCallCount = function updateCallCount() {
    // If they set an expiration of 0 then a request can be sent unlimited number of times. Otherwise, it needs to
    // be decremented.
    if (this.expires > 0)
      this.remainingCalls -= 1;
    else if (this.expires === 0)
      this.remainingCalls = 1;
  };

  /**
   * Indicates if the request can be made.
   * @returns {boolean}
   */
  RequestEntry.prototype.canMakeRequest = function canMakeRequest() {
    return this.remainingCalls > 0;
  };

  /**
   * Returns whether or not this request has met its expected call count.
   * @returns {boolean}
   */
  RequestEntry.prototype.isExpectedCallCount = function expectedCallCount() {
    return (this.expires === 0) ? true : this.remainingCalls === 0;
  };

  /**
   * Request model
   * @param {String} method (GET, POST, PUT, DELETE)
   * @param {String} requestUrl
   * @param {Object} data
   * @param {Object} headers
   * @constructor
   */
  function Request(method, requestUrl, data, headers) {
    this.method = method;
    this.url = requestUrl;
    this.data = data;
    this.headers = headers;

    // Is this a get request? If so, we need to look at the query parameters and set them to be the request data.
    if (this.method === config.methods.GET) {
      var getUrl = url.parse(this.url);
      this.data = querystring.parse(getUrl.query);
    }
  }

  /**
   * Response model
   * @param {String} status
   * @param {Object} headers
   * @param {Object} [data]
   * @constructor
   */
  function Response(status, headers, data) {
    this.status = status;
    this.data = data;
    this.headers = headers;
  }

  return {
    RequestEntry: RequestEntry,
    Request: Request,
    Response: Response
  };
};
