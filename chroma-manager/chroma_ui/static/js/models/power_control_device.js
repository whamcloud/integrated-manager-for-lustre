(function (_) {
  'use strict';

  function PowerControlDeviceModel(baseModel, PowerControlDeviceOutlet) {
    /**
     * @description Flattens nested device resources before save or update to server.
     * @param {object} data
     * @returns {string}
     */
    function transformRequest(data) {
      var flatData = _.cloneDeep(data);
      //flatten outlets.
      flatData.outlets = _.pluck(data.outlets, 'resource_uri');
      //flatten device_type.
      flatData.device_type = data.device_type.resource_uri;

      delete flatData.not_deleted;

      return angular.toJson(flatData);
    }

    /**
     * @description sorts a device's outlets then turns each into a PowerControlDeviceOutlet instance.
     * @param {PowerControlDeviceModel} device
     */
    function vivifyOutlets(device) {
      device.outlets.sort(function (a, b) {
        var v1 = a.identifier;
        var v2 = b.identifier;

        if (v1 === v2) {
          return 0;
        }

        return v1 < v2 ? -1 : 1;
      });

      device.outlets = device.outlets.map(function (outlet) {
        return new PowerControlDeviceOutlet(outlet);
      });
    }

    /**
     * @description Represents a power control device and it's outlets.
     * @class PowerControlDeviceModel
     * @returns {PowerControlDeviceModel}
     * @constructor
     */
    return baseModel({
      url: '/api/power_control_device/:powerControlDeviceId',
      params: {powerControlDeviceId: '@id'},
      actions: {
        query: {
          patch: function (devices) {
            devices.forEach(vivifyOutlets);
          }
        },
        save: {
          transformRequest: transformRequest,
          patch: vivifyOutlets
        },
        update: {
          transformRequest: transformRequest,
          patch: vivifyOutlets
        }
      },
      methods: {
        /**
         * @description Re-assigns the outlets based on a new assignment list.
         * @param {object} host
         * @param {[]} outletIdentifiers
         */
        reAssignOutletHostIntersection: function (host, outletIdentifiers) {
          function findOutlets(notAssigned, outlet) {
            var alreadyAssigned = (outlet.host === host.resource_uri);
            var notInNewList = (outletIdentifiers.indexOf(outlet.identifier) === -1);

            return notAssigned ?
              !alreadyAssigned && !notInNewList :
              alreadyAssigned && notInNewList;
          }

          // find outlets that were plugged into host but are now removed.
          var toUpdate = this.outlets
            .filter(findOutlets.bind(null, false))
            .map(function unassignOutlets(outlet) {
              outlet.host = null;
              return outlet;
            });

          // Assign new identifiers and update.
          this.outlets
            .filter(findOutlets.bind(null, true))
            .forEach(function assignOutlet(outlet) {
              outlet.host = host.resource_uri;
              toUpdate.push(outlet);
            });

          toUpdate.forEach(function runUpdate(outlet) {
            angular.copy(outlet).$update();
          });
        },
        /**
         * @description Returns a flat list of what outlets are assigned at the intersection of a host and pdu.
         * @param {object} host
         * @returns {Array}
         */
        getOutletHostIntersection: function (host) {
          return this.outlets.filter(function (outlet) {
            return outlet.host === host.resource_uri;
          });
        },
        format: function (value) {
          return _.pluck(value, 'identifier');
        }
      }
    });
  }

  angular.module('models')
    .factory('PowerControlDeviceModel', ['baseModel', 'PowerControlDeviceOutlet', PowerControlDeviceModel]);
}(window.lodash));

