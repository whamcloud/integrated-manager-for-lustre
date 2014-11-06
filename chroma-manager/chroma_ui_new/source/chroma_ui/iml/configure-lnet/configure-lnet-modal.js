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

  angular.module('configure-lnet-module')
    .controller('ConfigureLnetModalCtrl', ['$scope', '$modalInstance', 'networkInterfaceSpark',
      'hostSpark', 'throwIfError', 'requestSocket', 'openCommandModal', 'LNET_OPTIONS', 'createCommandSpark',
      function ConfigureLnetModalCtrl ($scope, $modalInstance, networkInterfaceSpark, hostSpark,
                                       throwIfError, requestSocket, openCommandModal, LNET_OPTIONS,
                                       createCommandSpark) {
        $scope.configureLnet = {
          options: LNET_OPTIONS,
          /**
           * Closes the modal, passing a skip boolean.
           * @param {Boolean} skip
           */
          save: function save (skip) {
            this.message = 'Saving';

            var spark = requestSocket();

            spark.sendPost('/nid', {
              json: {
                objects: _.pluck($scope.configureLnet.networkInterfaces, 'nid')
              }
            }, true)
              .then(function closeModal (data) {
                $modalInstance.close();

                return data;
              })
              .then(function (data) {
                if (skip || data == null)
                  return;

                var spark = createCommandSpark([data.body.command]);
                openCommandModal(spark)
                  .result.then(function endSpark () {
                    spark.end();
                  });
              })
              .finally(function () {
                spark.end();
              });
          },
          /**
           * Dismisses the modal.
           */
          close: function close () {
            $modalInstance.dismiss('cancel');
          },
          /**
           * Diffs a record against a initial and remote representation
           * to figure out what changed
           * @param {Object} record
           * @returns {{params: Object, type: String}}
           */
          getDiff: function getDiff (record) {
            var initialRecord = findById(record.id, initial);
            var remoteRecord = findById(record.id, last);
            var hasChangedInitial = compareTo(initialRecord);
            var remoteChanged = hasChangedInitial(last);
            var hasChangedLocal = compareTo(record);
            var localChanged = hasChangedLocal(initial);

            if (localChanged && remoteChanged)
              return {
                params: {
                  initial : getOption(initialRecord.nid.lnd_network),
                  remote: getOption(remoteRecord.nid.lnd_network)
                },
                type: 'conflict'
              };
            else if (localChanged)
              return {
                params: {
                  remote: getOption(remoteRecord.nid.lnd_network)
                },
                type: 'local'
              };
            else if (remoteChanged)
              return {
                params: {
                  remote: getOption(remoteRecord.nid.lnd_network)
                },
                type: 'remote'
              };

            function getOption (value) {
              return _.find($scope.configureLnet.options, { value: value }).name;
            }
          },
          /**
           * Fires when a Luster Network select box is changed.
           * If the local value has changed from initial
           * but not from remote it means we are out of sync.
           * @param {Object} record
           */
          onChange: function onChange (record) {
            var changed = compareTo(record);

            if (changed(initial) && !changed(last))
              setToRemote(record, last, initial);
          },
          /**
           * Given a record, cleans the current and initial values.
           * Also makes sure any other dirty values do not contain the clean value.
           * @param {Object} record
           */
          clean: function clean (record) {
            if ($scope.configureLnet.getDiff(record) == null)
              return;

            setToRemote(record, last, initial);

            //Find any records that have same lnd_network and are dirty
            //Clean them.
            _.chain($scope.configureLnet.networkInterfaces)
              .without(record)
              .where({ nid: { lnd_network: record.nid.lnd_network } })
              .value()
              .forEach($scope.configureLnet.clean);
          }
        };

        /**
         * Updates the host for this modal.
         * @param {Object} response
         */
        hostSpark.onValue('data', throwIfError(function onDataValue (response) {
          $scope.configureLnet.host = response.body;
        }));

        var last, initial;

        /**
         * Sets the initial current and last values.
         * @param {Object} response
         */
        networkInterfaceSpark.onValue('pipeline', function onPipelineValue (response) {
          $scope.configureLnet.resolved = true;

          initial = (initial ? initial.concat(diffOnId(response, initial)) : angular.copy(response));

          $scope.configureLnet.networkInterfaces = (!$scope.configureLnet.networkInterfaces ?
            angular.copy(response) :
            unionOnId($scope.configureLnet.networkInterfaces, response)
              .concat(diffOnId(response, $scope.configureLnet.networkInterfaces)));

          last = response;
        });

        /**
         * Destroys the scopes.
         */
        $scope.$on('$destroy', function onDestroy () {
          hostSpark.end();
          networkInterfaceSpark.end();
        });

        /**
         * Find items that are in left, but not right.
         * @type {Function}
         */
        var diffOnId = comparator(function predicate (right, search) {
          return _.where(right, search).length === 0;
        });

        /**
         * Finds items that are in both left and right sides.
         * @type {Function}
         */
        var unionOnId = comparator(function predicate (right, search) {
          return _.find(right, search);
        });

        /**
         * HOF. Filters items from left and right based on a predicate.
         * @param {Function} predicate
         * @returns {Function}
         */
        function comparator (predicate) {
          return function matcher (left, right) {
            return left.filter(function (item) {
              var search = _.pick(item, 'id');

              return predicate(right, search);
            });
          };
        }

        /**
         * HOF. Given an item, finds a matching lnd_network.
         * @param {Object} item
         * @returns {Function}
         */
        function compareTo (item) {
          return function changed (other) {
            var match = findById(item.id, other);

            return item.nid.lnd_network !== match.nid.lnd_network;
          };
        }

        /**
         * Updates the nid.lnd_network for a local and initial record to the value of a remote one.
         * @param {Object} record
         * @param {Array} last
         * @param {Array} initial
         */
        function setToRemote (record, last, initial) {
          var remoteRecord = findById(record.id, last);
          var initialRecord = findById(record.id, initial);

          record.nid.lnd_network = initialRecord.nid.lnd_network = remoteRecord.nid.lnd_network;
        }

        /**
         * Finds an item by Id
         * @param {Number} id
         * @param {Array} search
         * @returns {Object|undefined}
         */
        function findById (id, search) {
          return _.find(search, { id: id });
        }
      }
    ])
    .factory('openLnetModal', ['$modal', function openLnetModalFactory ($modal) {
      return function openLnetModal (host) {
        return $modal.open({
          templateUrl: 'iml/configure-lnet/assets/html/configure-lnet-modal.html',
          controller: 'ConfigureLnetModalCtrl',
          windowClass: 'configure-lnet-modal',
          resolve: {
            /**
             * Resolves a spark representing the provided host
             * @param {Function} requestSocket
             * @returns {Object}
             */
            hostSpark: ['requestSocket', function hostSpark (requestSocket) {
              var spark = requestSocket();

              spark.setLastData({
                statusCode: 200,
                body: host
              });
              spark.sendGet(host.resource_uri);

              return spark;
            }],
            /**
             * Resolves a spark representing a series of network interfaces.
             * @param {Function} requestSocket
             * @param {Function} throwIfError
             * @param {Object} LNET_OPTIONS
             */
            networkInterfaceSpark: ['requestSocket', 'throwIfError', 'LNET_OPTIONS',
              function getNetworkInterfaceSpark (requestSocket, throwIfError, LNET_OPTIONS) {
                var spark = requestSocket();

                spark.addPipe(throwIfError(function transform (response) {
                  response.body.objects.forEach(function addNidIfMissing (item) {
                    if (!item.nid)
                      item.nid = {
                        lnd_network: LNET_OPTIONS[0].value,
                        network_interface: item.resource_uri
                      };
                  });

                  return response.body.objects;
                }));

                spark.sendGet('/network_interface', {
                  qs: {
                    host__id: host.id
                  }
                });

                return spark;
              }]
          }
        });
      };
    }]);
}());
