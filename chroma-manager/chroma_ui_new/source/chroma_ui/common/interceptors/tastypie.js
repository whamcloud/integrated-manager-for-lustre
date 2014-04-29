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

  angular.module('interceptors')
    .factory('tastypieInterceptor', [function tastypieInterceptor() {
      return {
        /**
         * A Factory function that intercepts successful http responses
         * and puts the meta property at a higher level if it is a tastypie generated response.
         * @returns {object} The transformed response.
         */
        response: function (resp) {
          var fromTastyPie = _.isObject(resp.data) && _.isObject(resp.data.meta) && Array.isArray(resp.data.objects);

          // If we got data, and it looks like a tastypie meta/objects body
          // then pull off the meta.
          if (fromTastyPie) {
            var temp = resp.data.objects;

            resp.props = resp.data;
            delete resp.data.objects;

            resp.data = temp;
          }

          // Return the response for further processing.
          return resp;
        }
      };
    }])
    .config(['$httpProvider', function ($httpProvider) {
      // register the interceptor.
      $httpProvider.interceptors.push('tastypieInterceptor');
    }]);
}());
