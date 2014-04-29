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

  angular.module('exception').config(['$provide', function ($provide) {
    $provide.decorator('$exceptionHandler', ['$injector', '$delegate', function ($injector, $delegate) {
      var triggered,
        cache = {};

      return function(exception, cause) {
        //Always hit the delegate.
        $delegate(exception, cause);

        if (triggered) return;

        triggered = true;

        // Lazy Load to avoid a $rootScope circular dependency.
        var exceptionModal = get('exceptionModal'),
          ClientErrorModel = get('ClientErrorModel'),
          $document = get('$document');


        exceptionModal({
          resolve: {
            exception: function () { return exception; },
            cause: function () { return cause; }
          }
        });

        //We are not interested in saving server generated errors.
        if (exceptionOrEmptyObj().response) return;

        var err = new ClientErrorModel();

        err.stack = exceptionOrEmptyObj().stack;
        err.message = exceptionOrEmptyObj().message;
        err.url = $document[0].URL;
        err.cause = cause;

        err.$save();

        function exceptionOrEmptyObj () { return exception || {}; }
      };

      function get(serviceName) {
        return cache[serviceName] || (cache[serviceName] = $injector.get(serviceName));
      }
    }]);
  }]);
}());
