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


(function () {
  'use strict';

  function ExceptionModalCtrl ($scope, $document, $parse, exception, MODE, stackTraceContainsLineNumber,
                               sendStackTraceToRealTime) {

    $scope.exceptionModal = {
      messages: [],
      reload: function reload () {
        $document[0].location.reload(true);
      }
    };

    $scope.exceptionModal.messages = new PropLookup($parse, exception)
      .add('cause')
      .add({name: 'statusCode', alias: 'Status Code'})
      .path('response')
      .add({name: 'status', alias: 'Response Status'})
      .path('response.data')
      .add({name: 'error_message', alias: 'Error Message'})
      .add({name: 'traceback', alias: 'Server Stack Trace', transform: lookupAnd(multiLineTrim)})
      .path('response')
      .add({name: 'headers', alias: 'Response Headers', transform: lookupAnd(stringify)})
      .path('response.config')
      .add('method')
      .add('url')
      .add({name: 'headers', alias: 'Request Headers', transform: lookupAnd(stringify)})
      .add({name: 'data', transform: lookupAnd(stringify)})
      .reset()
      .add('name')
      .add('message')
      .add({name: 'stack', alias: 'Client Stack Trace', transform: lookupAnd(multiLineTrim)})
      .get();

    if (!exception.statusCode && MODE === 'production' && stackTraceContainsLineNumber(exception)) {
      $scope.exceptionModal.loadingStack = true;
      sendStackTraceToRealTime(exception).then(function updateData (newException) {
        $scope.exceptionModal.loadingStack = false;
        _.find($scope.exceptionModal.messages, {name: 'Client Stack Trace'}).value = newException.stack;
      });
    }

    /**
     * HOF Lookup and do something
     * @param {Function} func
     * @returns {Function}
     */
    function lookupAnd (func) {
      return function (name, spot) {
        var value = spot[name];

        if (!value) return false;

        try {
          return func(value);
        } catch (e) {
          return String(value).valueOf();
        }
      };
    }

    /**
     * Stringify's a value
     * @param {*} value
     * @returns {String}
     */
    function stringify (value) {
      return JSON.stringify(value, null, 2);
    }

    /**
     * Multi line trim
     * @param {String} value
     * @returns {String}
     */
    function multiLineTrim (value) {
      return value.split('\n').map(function (line) {
        return line.trim();
      }).join('\n');
    }
  }

  angular.module('exception')
    .controller('ExceptionModalCtrl', ['$scope', '$document', '$parse', 'exception', 'MODE',
      'stackTraceContainsLineNumber', 'sendStackTraceToRealTime', ExceptionModalCtrl])
    .factory('stackTraceContainsLineNumber', [function stackTraceContainsLineNumbers () {
      var regex = /^.+\:\d+\:\d+.*$/;

      return function stackTraceContainsLineNumbers (stackTrace) {
        return stackTrace.stack.split('\n')
          .some(function verifyStackTraceContainsLineNumbers (val) {
            var match = val.trim().match(regex);
            return (match == null) ? false : match.length > 0;
          });
      };
    }]).factory('sendStackTraceToRealTime', ['$rootScope', 'socket', '$q',
      function sendStackTraceToRealTime ($rootScope, socket, $q) {

      /**
       * Sends the stack trace to the real time service
       * @param {Object} exception
       * @returns {$q.promise}
       */
      return function sendStackTraceToRealTime (exception) {
        var deferred = $q.defer();
        var spark = socket('request');

        spark.send('req', {
            path: '/srcmap-reverse',
            options: {
              method: 'post',
              cause: exception.cause,
              message: exception.message,
              stack: exception.stack,
              url: exception.url
            }
          },
          function processResponse (response) {
            // Keep the original stack trace if reformatting of the stack trace failed.
            if (response.body && response.body.data)
              exception.stack = response.body.data;

            deferred.resolve(exception);
          });

        return deferred.promise;
      };
    }]);

  /**
   * Helper class that builds a message list from a given object
   * @param {function} $parse
   * @param {object} obj
   * @constructor
   */
  function PropLookup ($parse, obj) {
    this._$parse = $parse;
    this._obj = obj;
    this.messages = [];

    this.reset();
  }

  /**
   * Moves the spot to the parsed expression on the object.
   * @param {string} expression
   * @returns {PropLookup} This instance for chaining.
   */
  PropLookup.prototype.path = function path (expression) {
    this.spot = this._$parse(expression)(this._obj);

    return this;
  };

  /**
   * Resets the spot to the top of the object.
   * @returns {PropLookup} This instance for chaining.
   */
  PropLookup.prototype.reset = function path () {
    this.spot = this._obj;

    return this;
  };

  /**
   * Adds the item to the messages if it is found.
   * @param {string|object} item
   * @returns {PropLookup} This instance for chaining
   */
  PropLookup.prototype.add = function add (item) {
    if (!this.spot) return this;

    if (_.isString(item)) item = {name: item};

    if (!_.isPlainObject(item)) return this;

    _.defaults(item, {
      transform: function (name, spot) {
        return spot[name];
      },
      alias: item.name
    });

    var value = item.transform(item.name, this.spot);

    if (value)
      this.messages.push({name: item.alias, value: value});

    return this;
  };

  /**
   * Returns the list of messages.
   * @returns {Array} The messages.
   */
  PropLookup.prototype.get = function get () {
    return this.messages;
  };

}());
