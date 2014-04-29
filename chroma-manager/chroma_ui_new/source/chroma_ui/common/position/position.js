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

  /**
   * Helper class, responsible for positioning.
   * @constructor
   */
  function Position($window) {
    this.$window = $window;

    this.DIRECTIONS = {
      TOP: 'top',
      BOTTOM: 'bottom',
      RIGHT: 'right',
      LEFT: 'left'
    };


    this.defaults = {};

    this.defaults[this.DIRECTIONS.TOP] = {
      position: function (tooltipPositioner) {
        return {
          top: (tooltipPositioner.height * -1) + 'px',
          left: asCalc(tooltipPositioner.width / 2),
          'min-width': tooltipPositioner.width + 'px'
        };
      },
      overflows: function (windowPositioner, tooltipPositioner) {
        return tooltipPositioner.top < windowPositioner.top;
      }
    };

    this.defaults[this.DIRECTIONS.RIGHT] = {
      position: function (tooltipPositioner) {
        return {
          top: asCalc(tooltipPositioner.height / 2),
          left: '100%',
          'min-width': tooltipPositioner.width + 'px'
        };
      },
      overflows: function (windowPositioner, tooltipPositioner) {
        return tooltipPositioner.right > windowPositioner.right;
      }
    };

    this.defaults[this.DIRECTIONS.LEFT] = {
      position: function (tooltipPositioner) {
        return {
          top: asCalc(tooltipPositioner.height / 2),
          left: (tooltipPositioner.width * -1) + 'px',
          'min-width': tooltipPositioner.width + 'px'
        };
      },
      overflows: function (windowPositioner, tooltipPositioner) {
        return tooltipPositioner.left < windowPositioner.left;
      }
    };


    this.defaults[this.DIRECTIONS.BOTTOM] = {
      position: function (tooltipPositioner) {
        return {
          top: '100%',
          left: asCalc(tooltipPositioner.width / 2),
          'min-width': tooltipPositioner.width + 'px'
        };
      },
      overflows: function (windowPositioner, tooltipPositioner) {
        return tooltipPositioner.bottom > windowPositioner.bottom;
      }
    };
  }

  Position.prototype.positioner = function (element) {
    if (typeof element.getBoundingClientRect === 'function') {
      return positionerFactory(function () {
        return element.getBoundingClientRect();
      }, this.DIRECTIONS);
    } else if (element === this.$window ) {
      return positionerFactory(function () {
        return {
          top: 0,
          left: 0,
          right: element.innerWidth,
          bottom: element.innerHeight,
          height: element.innerHeight,
          width: element.innerWidth
        };
      }, this.DIRECTIONS);
    }
  };

  Position.prototype.position = function (direction, tooltipPositioner) {
    return this.defaults[direction].position(tooltipPositioner);
  };

  Position.prototype.overflows = function (direction, windowPositioner, tooltipPositioner) {
    return this.defaults[direction].overflows(windowPositioner, tooltipPositioner);
  };

  function positionerFactory(positionFinder, DIRECTIONS) {
    var props = _.values(DIRECTIONS).concat('height', 'width');

    var propertiesObject = props.reduce(function (obj, prop) {
      obj[prop] = {
        enumerable: true,
        get: function () {
          return positionFinder()[prop];
        }
      };

      return obj;
    }, {});

    return Object.create(Object.prototype, propertiesObject);
  }

  function asCalc(dimension) {
    var prefix = new RegExp('AppleWebKit/').test(navigator.userAgent) ? '-webkit-' : '';
    return '%scalc(50%% - %spx)'.sprintf(prefix, dimension);
  }

  angular.module('position').service('position', ['$window', Position]);
}());
