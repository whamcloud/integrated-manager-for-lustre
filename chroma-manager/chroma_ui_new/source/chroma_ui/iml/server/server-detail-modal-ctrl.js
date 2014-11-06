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

  angular.module('server').controller('ServerDetailModalCtrl',
    ['$scope', '$modalInstance', 'item', 'itemScope', 'serverSpark',
      'selectedServers', 'overrideActionClick',
      function ServerDetailModalCtrl ($scope, $modalInstance, item, itemScope, serverSpark,
                                      selectedServers, overrideActionClick) {

        var spark = serverSpark();

        $scope.serverDetailModal = {
          jobMonitorSpark: itemScope.jobMonitorSpark,
          alertMonitorSpark: itemScope.alertMonitorSpark,
          /**
           * Rejects the modal.
           */
          close: function close () {
            $modalInstance.dismiss('close');
          },
          /**
           * Getter method that retrieves the item data from the original scope. It must be
           * retrieved from the original scope or the data will be stale.
           * @returns {Object}
           */
          get item () {
            var myItem = _.find(itemScope.servers.objects, {id: item.id});
            if (myItem == null)
              this.removed = true;
            else
              this.currentItem = myItem;

            return this.currentItem;
          },
          closeAlert: function closeAlert (index) {
            this.alerts.splice(index, 1);
          },
          address: item.address,
          alerts: [
            {
              msg: 'The information below describes the last state of ' +
                item.address + ' before it was removed.'
            }
          ],
          overrideActionClick: overrideActionClick(spark),
          currentItem: null,
          removed: false
        };

        spark.onValue('data', function handler (response) {
          if ('error' in response)
            throw response.error;

          selectedServers.addNewServers(response.body.objects);
        });
      }]).factory('openServerDetailModal', ['$modal',
      function openServerDetailModalFactory ($modal) {

        /**
         * Opens the server detail modal
         * {Object} item
         * {Object} itemScope The scope in which the updated item will be retrieved from
         */
        return function openServerDetailModal (item, itemScope) {

          $modal.open({
            templateUrl: 'iml/server/assets/html/server-detail-modal.html',
            controller: 'ServerDetailModalCtrl',
            keyboard: false,
            backdrop: 'static',
            resolve: {
              item: function getItem () {
                return item;
              },
              itemScope: function getItemScope () {
                return itemScope;
              }
            }
          });
        };
      }]);
}());
