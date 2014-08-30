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

  angular.module('dashboard')
    .controller('DashboardFilterCtrl',
      ['$scope', '$location', 'streams', 'help', 'dashboardPath', '$$rAF', DashboardFilterCtrl]);

  function DashboardFilterCtrl($scope, $location, streams, help, dashboardPath, $$rAF) {
    /**
     * Represents a base type fs and server inherit from.
     * @type {{isSelected: isSelected, selectedItem: Object, selectedItem: Object}}
     */
    var type = {
      /**
       * Checks if this type is selected.
       * @returns {boolean}
       */
      isSelected: function () {
        return this.selectedItem != null;
      },
      /**
       * Gets the selected item.
       * @returns {Object}
       */
      get selectedItem () {
        return this._selectedItem;
      },
      /**
       * Sets the selected item.
       * Ends this type's target stream
       * and starts a new one with the new selected id.
       * @param {Object} newSelectedItem
       */
      set selectedItem (newSelectedItem) {
        this._selectedItem = newSelectedItem;

        this.targetStream.end();

        this.selectedTarget = null;

        if (newSelectedItem != null) {
          var params = {
            qs: { limit: 0 },
            jsonMask: 'objects(id,label,kind)'
          };
          params.qs[this.ID_NAME] = newSelectedItem.id;

          this.targetStream.start(params);
        }
      }
    };

    $scope.filter = {
      fsData: {},
      fsTargetData: {},
      serverData: {},
      serverTargetData: {},
      /**
       * Sets the type.
       * Ends the current type stream
       * and starts the new type's stream.
       * @param {object} newType
       */
      set type (newType) {
        if (this._type != null) {
          this._type.stream.end();
          this._type.targetStream.end();
        }

        newType.stream.start({
          qs: {limit: 0},
          jsonMask: 'objects(id,label)'
        });

        this._type = newType;
      },
      /**
       * Gets the type
       * @returns {Object}
       */
      get type () {
        return this._type;
      },
      /**
       * Returns the stream data for the current type.
       * @returns {Object}
       */
      get typeStream () {
        return this[this.type.NAME + 'Data'];
      },
      /**
       * Returns the target data for the current type.
       * @returns {Object}
       */
      get typeTargetStream () {
        return this[this.type.NAME + 'TargetData'];
      },
      /**
       * Called by the popover, watches for property changes that cause a resize.
       * @param {Object} actions
       */
      work: function work(actions) {
        $scope.$on('$locationChangeSuccess', actions.hide);
        $scope.recalculate = actions.recalculate;
      },
      /**
       * Called when filter is updated.
       * Looks at the selected items and moves
       * the path.
       */
      onFilterView: function () {
        var params = {};

        if (this.type.selectedItem)
          params.type = {
            name: this.type.NAME,
            id: this.type.selectedItem.id
          };

        if (this.type.selectedTarget)
          params.target = {
            name: this.type.selectedTarget.kind,
            id: this.type.selectedTarget.id
          };

        var path = dashboardPath.buildPath(params);

        $location.path(path);
      }
    };

    // Listen for a change in the streams. Recalculate the position of the popup if any ofthem change.
    $scope.$watchCollection('[filter.type, filter.type.selectedItem, filter.type.selectedTarget, ' +
      'filter.typeTargetStream.objects.length]',

      function () {
        if ($scope.recalculate) {
          $$rAF($scope.recalculate);
        }
    });

    /**
     * Extends base type for a fs.
     * @typedef {Object} fs
     * @type {type}
     */
    $scope.filter.fs = Object.create(type);
    _.extend($scope.filter.fs, {
      NAME: 'fs',
      ID_NAME: 'filesystem_id',
      LABEL: 'File System',
      help: help.get('dashboard_filter_fs'),
      stream: streams.fileSystemStream('filter.fsData', $scope),
      targetStream: streams.targetStream('filter.fsTargetData', $scope)
    });

    /**
     * Extends base type for a server.
     * @typedef {Object} server
     * @type {type}
     */
    $scope.filter.server = Object.create(type);
    _.extend($scope.filter.server, {
      NAME: 'server',
      ID_NAME: 'host_id',
      LABEL: 'Server',
      help: help.get('dashboard_filter_server'),
      stream: streams.hostStream('filter.serverData', $scope),
      targetStream: streams.targetStream('filter.serverTargetData', $scope)
    });

    $scope.filter.type = $scope.filter.fs;
  }
}());
