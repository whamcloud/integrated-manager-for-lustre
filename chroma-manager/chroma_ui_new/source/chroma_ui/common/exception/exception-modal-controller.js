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

  angular.module('exception')
    .controller('ExceptionModalCtrl', ['$scope', '$document', 'exception',
      'stackTraceContainsLineNumber', 'sendStackTraceToRealTime', ExceptionModalCtrl]);

  function ExceptionModalCtrl ($scope, $document, exception, stackTraceContainsLineNumber, sendStackTraceToRealTime) {
    $scope.exceptionModal = {
      messages: [],
      reload: function reload () {
        $document[0].location.reload(true);
      }
    };

    if (!exception.statusCode && stackTraceContainsLineNumber(exception)) {
      $scope.exceptionModal.loadingStack = true;
      sendStackTraceToRealTime(exception)
        .then(function updateData (newException) {
          $scope.exceptionModal.loadingStack = false;
          $scope.exceptionModal.messages
            .filter(fp.eqLens(fp.lensProp('name'))({name: 'Client Stack Trace'}))
            .map(fp.lensProp('value').set(newException.stack));

          if (!$scope.$$phase)
            $scope.$digest();
        });
    }

    /**
     * Stringify's a value
     * @param {*} value
     * @returns {String}
     */
    var stringify = lookupAnd(function stringify (value) {
      return JSON.stringify(value, null, 2);
    });

    /**
     * Multi line trim
     * @param {String} value
     * @returns {String}
     */
    var multiLineTrim = lookupAnd(function multiLineTrim (value) {
      return value.split('\n')
        .map(function (line) {
          return line.trim();
        }).join('\n');
    });

    var buildMessage = fp.curry(5, function buildMessage (arr, err, path, top, opts) {
      opts = _.clone(opts || {});
      _.defaults(opts, {
        transform: fp.identity,
        name: top
      });

      var item = fp.safe(1, path, undefined)(err);

      if (!item)
        return;

      arr.push({
        name: opts.name,
        value: opts.transform(item)
      });
    });

    var addSection = buildMessage($scope.exceptionModal.messages, exception);

    addSection(fp.lensProp('name'), 'name', {});
    addSection(fp.lensProp('message'), 'message', {});
    addSection(fp.lensProp('statusCode'), 'statusCode', { name: 'Status Code' });
    addSection(fp.lensProp('stack'), 'stack', { name: 'Client Stack Trace', transform: multiLineTrim });
    addSection(fp.lensProp('cause'), 'cause', {});

    var responseLens = fp.lensProp('response');
    addSection(fp.flowLens(responseLens, fp.lensProp('status')), 'status', { name: 'Response Status' });
    addSection(fp.flowLens(responseLens, fp.lensProp('headers')), 'headers', { name: 'Response Headers',
      transform: stringify });

    var dataLens = fp.flowLens(responseLens, fp.lensProp('data'));
    addSection(fp.flowLens(dataLens, fp.lensProp('error_message')), 'error_message', { name: 'Error Message' });
    addSection(fp.flowLens(dataLens, fp.lensProp('traceback')), 'traceback', { name: 'Server Stack Trace',
      transform: multiLineTrim });

    var configLens = fp.flowLens(responseLens, fp.lensProp('config'));
    addSection(fp.flowLens(configLens, fp.lensProp('method')), 'method', {});
    addSection(fp.flowLens(configLens, fp.lensProp('url')), 'url', {});
    addSection(fp.flowLens(configLens, fp.lensProp('headers')), 'headers', { name: 'Request Headers',
      transform: stringify });
    addSection(fp.flowLens(configLens, fp.lensProp('data')), 'data', { transform: stringify });


    /**
     * HOF Lookup and do something
     * @param {Function} func
     * @returns {Function}
     */
    function lookupAnd (func) {
      return function (value) {
        if (!value) return false;

        try {
          return func(value);
        } catch (e) {
          return String(value).valueOf();
        }
      };
    }
  }

  var regex = /^.+\:\d+\:\d+.*$/;

  angular.module('exception')
    .value('stackTraceContainsLineNumber', function stackTraceContainsLineNumbers (stackTrace) {
      return stackTrace.stack.split('\n')
        .some(function verifyStackTraceContainsLineNumbers (val) {
          var match = val.trim().match(regex);
          return (match == null) ? false : match.length > 0;
        });
    })
    .factory('sendStackTraceToRealTime', ['$rootScope', 'socket', '$q',
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
}());
