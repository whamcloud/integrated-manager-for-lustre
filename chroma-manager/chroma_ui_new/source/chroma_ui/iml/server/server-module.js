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


angular.module('server', ['pdsh-parser-module', 'filters', 'socket-module', 'pdsh-module', 'command'])
  .controller('ServerCtrl', ['$scope', '$modal', 'pdshParser', 'pdshFilter', 'naturalSortFilter',
    'serverSpark', 'serverActions', 'selectedServers', 'openCommandModal',
    function ServerCtrl ($scope, $modal, pdshParser, pdshFilter, naturalSortFilter,
                         serverSpark, serverActions, selectedServers, openCommandModal) {
      'use strict';

      $scope.server = {
        maxSize: 10,
        itemsPerPage: 10,
        currentPage: 1,
        pdshFuzzy: false,
        hostnames: [],
        servers: {
          objects: []
        },
        actions: serverActions,
        selectedServers: selectedServers.servers,
        toggleType: selectedServers.toggleType,

        /**
         * Returns the current list of PDSH filtered hosts.
         * @returns {Array}
         */
        getFilteredHosts: function getFilteredHosts () {
          var filtered = pdshFilter(this.servers.objects, this.hostnames, this.getHostPath, this.pdshFuzzy);

          return naturalSortFilter(filtered, this.getHostPath, this.reverse);
        },

        /**
         * Returns the total number of entries in servers.objects.
         * @returns {Number}
         */
        getTotalItems: function getTotalItems () {
          // The total number of items is determined by the result of the pdsh filter
          if (this.hostnames.length === 0)
            return this.servers.objects.length;

          return this.getFilteredHosts().length;
        },

        /**
         * Called when the pdsh expression is updated.
         * @param {String} expression pdsh expression
         */
        pdshUpdate: function pdshUpdate (expression, hostnames) {
          if (hostnames != null) {
            this.hostnames = hostnames;
            this.currentPage = 1;
          }
        },

        /**
         * Used by filters to determine the context.
         * @param {Object} item
         * @returns {String}
         */
        getHostPath: function getHostPath (item) {
          return item.address;
        },

        /**
         * Sets the current page.
         * @param {Number} pageNum
         */
        setPage: function setPage (pageNum) {
          this.currentPage = pageNum;
        },

        /**
         * Retrieves the items per page.
         * @returns {Number}
         */
        getItemsPerPage: function getItemsPerPage () {
          return +this.itemsPerPage;
        },

        /**
         * Sets the number of items per page.
         * @param {String} num
         */
        setItemsPerPage: function setItemsPerPage (num) {
          this.itemsPerPage = +num;
        },

        closeItemsPerPage: function closeItemsPerPage () {
          this.itemsPerPageIsOpen = false;
        },

        /**
         * Retrieves the sort class.
         * @returns {String}
         */
        getSortClass: function getSortClass () {
          return (this.inverse === true ? 'fa-sort-asc' : 'fa-sort-desc');
        },

        /**
         * Puts the table in editable mode.
         * @param {Boolean} editable
         */
        setEditable: function setEditable (editable) {
          $scope.server.editable = editable;
        },

        /**
         * Sets the action name to edit on
         * and puts table in editable mode.
         * @param {String} name
         */
        setEditName: function setEditName (name) {
          $scope.server.editName = name;
          $scope.server.setEditable(true);
        },

        /**
         * Given a value, returns the action cooresponding to it.
         * @param {String} value
         * @returns {Object}
         */
        getActionByValue: function getActionByValue (value) {
          return _.find(serverActions, { value: value });
        },

        /**
         * Returns the list of filtered, selected and non-disabled hosts.
         * @param {String} value
         * @returns {Array}
         */
        getSelectedHosts: function getSelectedHosts (value) {
          var action = this.getActionByValue (value);

          return this.getFilteredHosts()
            .filter(function pickSelected (host) {
              return selectedServers.servers[host.fqdn];
            })
            .filter(function pickEnabled (host) {
              if (!action.isDisabled)
                return true;

              return !action.isDisabled(host);
            });
        },

        /**
         * Runs a user selected server action.
         * @param {String} value
         */
        runAction: function runAction (value) {
          var action = this.getActionByValue(value);
          var hosts = this.getSelectedHosts(value);

          var modalInstance = $modal.open({
            templateUrl: 'iml/server/assets/html/confirm-server-action-modal.html',
            controller: 'ConfirmServerActionModalCtrl',
            windowClass: 'confirm-server-action-modal',
            keyboard: false,
            backdrop: 'static',
            resolve: {
              action: function getAction () { return action; },
              hosts: function getHosts () { return hosts; }
            }
          });

          modalInstance.result.then(function handler (data) {
            $scope.server.setEditable(false);

            if (data != null)
              openCommandModal({
                body: {
                  objects: [data]
                }
              });
          });
        }
      };

      var spark = serverSpark();
      spark.onValue('data', function handler (response) {
        if ('error' in response)
          throw response.error;

        $scope.server.servers = response.body;

        selectedServers.addNewServers(response.body.objects);
      });

      $scope.$on('$destroy', function onDestroy () {
        spark.end();
      });
    }]);
