//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
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


angular.module('charts').factory('chartParamMixins', ['d3', function (d3) {
  'use strict';


  /**
   * Wrapper that takes a config and optionally a target.
   * The config is cloned and captured.
   * @param {Object} config
   * @param {Object} [target]
   * @returns {Object} An object with properties matching the config but changed to getter/setter functions.
   */
  return function passConfigObj(config, target) {
    var clonedConfig = _.cloneDeep(config),
      obj = {},
      keys = Object.keys(clonedConfig),
      customGetterSetters = {
        margin: function (_) {
          if (!arguments.length) return clonedConfig.margin;

          clonedConfig.margin.top    = _.top    != null ? _.top    : clonedConfig.margin.top;
          clonedConfig.margin.right  = _.right  != null ? _.right  : clonedConfig.margin.right;
          clonedConfig.margin.bottom = _.bottom != null ? _.bottom : clonedConfig.margin.bottom;
          clonedConfig.margin.left   = _.left   != null ? _.left   : clonedConfig.margin.left;

          return obj;
        }
      };

    keys.forEach(function buildMixin(prop) {
      obj[prop] = customGetterSetters[prop] || getterSetterWrapper(prop);

      return obj;
    });

    if (target != null) {
      var args = [target, obj].concat(keys);

      d3.rebind.apply(d3, args);
    }

    return obj;

    /**
     * Returns a getterSetter function. prop is a captured param.
     * @param {String} prop
     * @returns {Function}
     */
    function getterSetterWrapper (prop) {
      /**
       * A generic getter setter function.
       */
      return function getterSetter(_) {
        if (!arguments.length) return clonedConfig[prop];

        clonedConfig[prop] = _;

        return obj;
      };
    }
  };
}]);