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

  angular.module('notification', [])
    .controller('NotificationCtrl', ['$scope', 'NotificationStream',
      function NotificationCtrl ($scope, NotificationStream) {
        var LIMIT = 99;

        $scope.notification = {
          status: {},
          /**
           * Returns the count or the limit if count > limit
           * @returns {Number}
           */
          get count () {
            if (this.aboveLimit)
              return LIMIT;

            return this.status.count;
          },
          /**
           * Is the count above the limit
           * @returns {boolean}
           */
          get aboveLimit () {
            return this.status.count > LIMIT;
          }
        };

        var notificationStream = NotificationStream.setup('notification.status', $scope);
        notificationStream.startStreaming();
      }
    ])
    .factory('NotificationStream', ['stream', function notificationStreamFactory (stream) {
      return stream('notification', 'httpGetHealth', {
        params: {},
        transformers: function setStatus(resp) {
          this.setter(resp.body);
        }
      });
    }]);
}());
