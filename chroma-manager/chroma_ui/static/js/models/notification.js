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

  angular.module('models').factory('notificationModel',
    ['baseModel', 'alertModel', 'eventModel', 'commandModel', 'paging', notificationModelFactory]);

  /**
   * Represents the notification API endpoint.
   * @param {Function} baseModel
   * @param {Function} AlertModel
   * @param {Function} EventModel
   * @param {Function} CommandModel
   * @param {Function} paging
   * @returns {Function}
   */
  function notificationModelFactory (baseModel, AlertModel, EventModel, CommandModel, paging) {
    return baseModel({
      url: '/api/notification',
      actions: {
        dismissAll: {
          url: '/api/notification/dismiss_all',
          method: 'PUT',
          isArray: false
        },
        query: {
          method: 'GET',
          isArray: true,
          interceptor: {
            /**
             * Casts the mixed response data of the notifications API to their respective types.
             * @param {Object} resp
             * @returns {Array}
             */
            response: function response (resp) {
              resp.resource = resp.data.map(function convertToType (item) {
                switch (item.type) {
                  case 'Command':
                    item = new CommandModel(item);
                    break;
                  case 'AlertState':
                    item = new AlertModel(item);
                    break;
                  case 'Event':
                    item = new EventModel(item);
                    break;
                  default:
                    throw new Error('Type not expected.');
                }

                return item;
              });

              resp.resource.paging = paging(resp.props.meta);

              return resp.resource;
            }
          }
        }
      }
    });
  }
}());
