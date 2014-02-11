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


angular.module('charts').factory('formatBytes', [function () {
  'use strict';

  var units = ['B', 'kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

  return function formatBytes(bytes, precision) {
    if (isNaN(parseFloat(bytes)) || !isFinite(bytes)) return '';
    precision = precision || 4;

    bytes = Math.max(bytes, 0);
    var pwr = Math.floor(Math.log(bytes) / Math.log(1024));
    pwr = Math.min(pwr, units.length - 1);
    pwr = Math.max(pwr, 0);
    bytes /= Math.pow(1024, pwr);
    return '%s %s'.sprintf((bytes).toPrecision(precision), units[pwr]);
  };

}]);
