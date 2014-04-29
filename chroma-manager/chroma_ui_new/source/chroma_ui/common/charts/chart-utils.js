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


angular.module('charts').factory('chartUtils', ['chartParamMixins', function (chartParamMixins) {
  'use strict';

  return {
    /**
     * Convenience to create a translate string
     * @param {Number} dx The x coordinate.
     * @param {Number} dy The y coordinate.
     * @returns {String}
     */
    translator: function translator(dx, dy) {
      return 'translate(' + dx + ',' + dy + ')';
    },
    /**
     * Convenience to prepend a string with a CSS class period.
     * @param {String} str
     * @returns {String}
     */
    cl: function cl(str) {
      return '.' + str;
    },
    /**
     * Convenience to get a node's bounding box.
     * @param selection A d3 selection
     * @returns {Object}
     */
    getBBox: function getBBox(selection) {
      return selection.node().getBBox();
    },
    /**
     * Exports the chartParamMixins in this object
     * @property chartParamMixins
     */
    chartParamMixins: chartParamMixins
  };
}]);

