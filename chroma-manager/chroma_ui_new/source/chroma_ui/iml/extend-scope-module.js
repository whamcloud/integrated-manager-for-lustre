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

angular.module('extendScope', [])
  .config(['$provide', function addHandleExceptionMethod ($provide) {
    return $provide.decorator('$rootScope', ['$delegate', '$exceptionHandler',
      function addExceptionHandler ($delegate, $exceptionHandler) {
        $delegate.handleException = fp.curry(1, $exceptionHandler);

        return $delegate;
      }]);
  }])
  .config(['$provide', function addLocalApplyMethod ($provide) {
    return $provide.decorator('$rootScope', ['$delegate', 'localApply',
      function addLocalApply ($delegate, localApply) {
        $delegate.localApply = localApply;

        return $delegate;
      }]);
  }])
  .factory('localApply', ['$exceptionHandler', function localApplyFactory ($exceptionHandler) {
    return function localApply (scope, fn) {
      try {
        if (typeof fn === 'function')
          return fn();
      } catch (e) {
        $exceptionHandler(e);
      } finally {
        try {
          if (!scope.$root.$$phase)
            scope.$digest();
        } catch (e) {
          $exceptionHandler(e);
          throw e;
        }
      }
    };
  }]);
