//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
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

var server;
var sockets = [];

/**
 * The webservice file, which receives requests, delegates them to a router, where the request is processed, and then
 * returns the response.
 * @param {Function} router
 * @param {Object} requestStore
 * @param {Object} mockStatus
 * @param {Object} config
 * @param {http} request
 * @param {url} url
 * @param {Logger} logger
 * @param {Object} fsReadThen
 * @param {Promise} Promise
 * @returns {Object}
 */
exports.wiretree = function webServiceModule(router, requestStore, mockStatus, config, request, url, logger, fsReadThen,
                                             Promise) {

  /**
   * Handles an incoming request.
   * @param {String} parsedUrl
   * @param {Object} request
   * @param {Object} response
   * @param {Object} body
   */
  function handleRequest(parsedUrl, request, response, body) {
    logger.logByLevel({
      DEBUG: [parsedUrl.pathname, 'Request received:'],
      TRACE: [{
        pathname: parsedUrl.pathname,
        body: (
          body
        ) ? body.toString() : undefined
      }, 'Request received']
    });

    if (body) {
      var jsonErrorMessage = 'JSON is not properly formed.';
      try {
        body = JSON.parse(body.toString());
      } catch (e) {
        logger.warn({
          body: body.toString()
        }, jsonErrorMessage);

        response.writeHead(config.status.BAD_REQUEST, config.standardHeaders);
        response.write(jsonErrorMessage);
        response.end();
        return;
      }
    }

    // Delegate the request to the router, where it will be processed and return a response.
    handleResponse(response, router(parsedUrl.pathname, request, body));
  }

  /**
   * Handles processing the response returned by the router
   * @param {Object} response
   * @param {Object} evaluatedResponse
   */
  function handleResponse(response, evaluatedResponse) {
    if (evaluatedResponse) {
      logger.trace({
        status: evaluatedResponse.status.toString(),
        response: evaluatedResponse.data
      }, 'Response received.');

      response.writeHead(evaluatedResponse.status.toString(), evaluatedResponse.headers);
      if (evaluatedResponse.data) {
          response.write(JSON.stringify(evaluatedResponse.data));
      }
      response.end();

    } else {
      var status = config.status.NOT_FOUND;

      logger.warn({
        status: config.status.NOT_FOUND,
        response: (status) ? status.toString() : undefined
      }, 'Request not found; no status');

      response.writeHead(status.toString(), config.standardHeaders);
      response.write(status.toString());
      response.end();
    }
  }

  /**
   * Handles a socket connection.
   * @param {http.Socket} socket
   */
  function handleSocketConnection(socket) {
    sockets.push(socket);
    socket.setTimeout(4000);
    socket.on('close', function () {
      // Remove the socket from the array using splice
      sockets.splice(sockets.indexOf(socket), 1);
    });
  }

  /**
   * Callback that is called when a request is received.
   * @param {Object} request
   * @param {Object} response
   */
  function onRequestReceived(request, response) {
    var parsedUrl = url.parse(request.url, true);
    var data;

    request.on('data', function handleData(chunk) {
      if (chunk) {
        data = data || '';
        data += chunk.toString();
      }
    });
    request.on('end', function handleEnd() {
      handleRequest(parsedUrl, request, response, data);
    });
  }

  /**
   * Reads in the key.pem and cert.pem files asynchronously and when finished it returns a promise with the
   * options object as a parameter.
   * @returns {Promise} A promise with the options object passed in as a parameter
   */
  function getCertificateFiles() {
    return Promise.all([fsReadThen(__dirname + '/key.pem'), fsReadThen(__dirname + '/cert.pem')])
      .then(function(res) {
        return Promise.resolve({
          key: res[0],
          cert: res[1]
        });
      });
  }

  /**
   * Calls the bounded createServer function and listens on the specified port. It also sets up a callback for  when
   * a connection is established. Finally, the server object is returned.
   * @param {Function} boundCreateServer
   * @param {Number} port
   * @returns {http.Server}
   */
  function executeService(boundCreateServer, port) {
    server = boundCreateServer(onRequestReceived).listen(port);
    server.on('connection', handleSocketConnection);
    server.on('clientError', logger.error.bind(logger));
    logger.info('Starting service on ' + config.requestProtocol + '://localhost:' + port);
    return server;
  }

  return {

    /**
     * Starts the service.
     * @returns {Promise} A promise with the server as the first argument
     */
    startService: function startService() {
      sockets = [];

      var promise;
      if (config.requestProtocol === 'https') {
        promise = getCertificateFiles().then(function createServiceWithProperBound(options) {
          return executeService(request.createServer.bind(request, options), config.port);
        });
      } else {
        promise = Promise.resolve(executeService(request.createServer, config.port));
      }

      return promise;
    },

    /**
     * Stops the service
     */
    stopService: function stopService () {
      return new Promise(function handler (resolve) {
        server.close(resolve);

        logger.info('Service stopping...');

        if (sockets.length > 0)
          logger.trace('Destroying ' + sockets.length + ' remaining socket connections.');

        // Make sure all sockets have been closed
        while (sockets.length > 0) {
          sockets.shift().destroy();
        }
      });
    },

    /**
     * Returns the number of connections based on the socket count.
     * @returns {Number}
     */
    getConnectionCount: function getConnectionCount() {
      return sockets.length;
    },

    /**
     * Flushes the entries in the request store and the requests in the mock state module.
     */
    flush: function flushEntries() {
      requestStore.flushEntries();
      mockStatus.flushRequests();
    }
  };
};
