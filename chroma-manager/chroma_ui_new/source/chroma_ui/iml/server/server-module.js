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


angular.module('server', ['pdsh-parser-module', 'filters'])
  .controller('ServerCtrl', ['$scope', 'pdshParser', 'pdshFilter',
    function ServerCtrl ($scope, pdshParser, pdshFilter) {
      'use strict';

      $scope.server = {
        maxSize: 10,
        itemsPerPage: 10,
        currentPage: 1,
        pdshFuzzy: false,
        hostnames: [],
        object: {
          created_at: '2014-08-21T13:23:25.183372+00:00',
          dismissed: false,
          host: '/api/host/2/',
          host_name: 'test00%s',
          id: 1,
          message: 'LNet started on server \'test002\'',
          resource_uri: '/api/event/450/',
          severity: 'INFO',
          subtype: 'AlertEvent',
          type: 'Event',
          lNet: 'LNet up',
          status: true
        },
        servers: {
          objects: []
        },

        /**
         * Returns the total number of entries in servers.objects
         * @returns {Number}
         */
        getTotalItems: function getTotalItems () {
          // The total number of items is determined by the result of the pdsh filter
          if (this.hostnames.length === 0) {
            return this.servers.objects.length;
          }

          return pdshFilter(this.servers.objects, this.hostnames, this.getHostPath, this.pdshFuzzy).length;
        },

        /**
         * Called when the pdsh expression is updated
         * @param {String} expression pdsh expression
         */
        pdshUpdate: function pdshUpdate (expression) {
          var expansion = pdshParser(expression);
          this.hostnames = [];
          if (expansion.expansion) {
            this.hostnames = expansion.expansion;
            this.currentPage = 1;
          }
        },

        /**
         * Used by filters to determine the context
         * @param {Object} item
         * @returns {String}
         */
        getHostPath: function (item) {
          return item.host_name;
        },

        /**
         * Sets the current page
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
         * Retrieves the sort class
         * @returns {String}
         */
        getSortClass: function getSortClass () {
          if (this.inverse === true) {
            return 'fa-sort-asc';
          } else {
            return 'fa-sort-desc';
          }
        },

        /**
         * Initializes the data structure for the table
         */
        initialize: function initialize () {
          // Initialize some test data to display the table
          for (var i = 0; i < 100; i += 1) {
            var newObj = _.clone(this.object, true);
            newObj.id = i;
            newObj.host_name = newObj.host_name.replace('%s', i.toString());
            this.servers.objects.push(newObj);
          }
        }
      };

      // Initialize the table data
      $scope.server.initialize();

    }]);
