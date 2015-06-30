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

  angular.module('readWriteHeatMap', ['charts', 'stream', 'filters'])
    .controller('ReadWriteHeatMapCtrl',
    ['$scope', '$location', '$filter', 'd3', 'ReadWriteHeatMapStream',
      'DURATIONS', 'formatBytes', ReadWriteHeatMapCtrl]);

  function ReadWriteHeatMapCtrl ($scope, $location, $filter, d3, ReadWriteHeatMapStream, DURATIONS, formatBytes) {
    var roundFilter = $filter('round');

    $scope.readWriteHeatMap = {
      data: [],
      onUpdate: function onUpdate (unit, size) {
        $scope.readWriteHeatMap.data.length = 0;

        var params = _.merge({
          qs: {
            unit: unit,
            size: size
          }
        }, $scope.params || {});

        readWriteHeatMapStream.restart(params);
      },
      toReadableType: toReadableType,
      options: {
        setup: function setup (chart) {
          chart.options({
            showYAxis: false,
            formatter: formatter,
            margin: { left: 50 }
          });

          chart.onMouseOver(mouseHandler(function (d) {
            return {
              date: d.x,
              ostName: d.key,
              bandwidth: formatter(d.z),
              readableType: toReadableType(readWriteHeatMapStream.type)
            };
          }));

          chart.onMouseMove(mouseHandler());

          chart.onMouseOut(mouseHandler(function () {
            return {
              isVisible: false
            };
          }));

          chart.onMouseClick(function mouseClickHandler (d, el) {
            var end;

            var start = el.__data__.x.toISOString(),
              next = el.nextSibling,
              id = el.__data__.id;

            if (next)
              end = next.__data__.x.toISOString();
            else
              end = new Date().toISOString();

            $scope.$apply(function () {
              $location.path('dashboard/jobstats/%s/%s/%s'.sprintf(id, start, end));
            });
          });

          chart.xAxis().showMaxMin(false);
        }
      },
      type: ReadWriteHeatMapStream.TYPES.READ_BYTES,
      TYPES: Object.keys(_.invert(ReadWriteHeatMapStream.TYPES)),
      toggle: function toggle (type) {
        readWriteHeatMapStream.switchType(type);
      },
      unit: DURATIONS.MINUTES,
      size: 10
    };

    var readWriteHeatMapStream = ReadWriteHeatMapStream.setup('readWriteHeatMap.data', $scope, $scope.params || {});

    readWriteHeatMapStream.type = ReadWriteHeatMapStream.TYPES.READ_BYTES;
    readWriteHeatMapStream.startStreaming({
      qs: {
        unit: $scope.readWriteHeatMap.unit,
        size: $scope.readWriteHeatMap.size
      }
    });

    /**
     * Given a type, normalizes it to a human readable version.
     * @param {String} type
     * @returns {String}
     */
    function toReadableType (type) {
      var readable = type
        .split('_')
        .splice(1)
        .join(' ')
        .replace('bytes', 'Byte/s')
        .replace('iops', 'IOPS');

      return (readable.charAt(0).toUpperCase() + readable.slice(1));
    }

    var thousandsFormat = d3.format(',');

    /**
     * Formats the heat map value.
     * @param {Number} z
     * @returns {String}
     */
    function formatter (z) {
      var dataType = readWriteHeatMapStream.type.split('_').pop();
      return (dataType === 'bytes' ? formatBytes(z, 3) + '/s' : thousandsFormat(roundFilter(z, 2)) + ' IOPS');
    }

    /**
     * Extends the scope right before mouse movement.
     * @param {Function} [overrides]
     * @returns {Function}
     */
    function mouseHandler (overrides) {
      if (!_.isFunction(overrides))
        overrides = fp.always({});

      return function (d) {
        $scope.$apply(function () {
          _.extend($scope.readWriteHeatMap, {
            isVisible: true,
            x: (d3.event.hasOwnProperty('offsetX') ? d3.event.offsetX : d3.event.layerX) + 50,
            y: (d3.event.hasOwnProperty('offsetY') ? d3.event.offsetY : d3.event.layerY) + 50
          }, overrides(d));
        });
      };
    }
  }
}());
