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


(function () {
  'use strict';

  //@TODO: This module is a stopgap. Remove when directives can be natively interpreted.

  function factory($rootScope, $compile) {

    /**
     * Helper function to compile a template.
     * @param {object|string} template DOM partial or string
     * @returns {object} compiled template
    */
    return function compileTemplate(template) {
      // NOTE: This is only being done because of the Angular in Backbone paradigm.
      var $scope = $rootScope.$new();

      return $scope.safeApply(function () {
        var link = $compile(template);
        var fragment = link($scope);

        return fragment.bind('$destroy', function () {
          $scope.safeApply(function () { $scope.$destroy(); });

          fragment.unbind('$destroy');
        });
      });
    };

  }

  angular.module('services').factory('compileTemplate', ['$rootScope', '$compile', factory]);
}());
