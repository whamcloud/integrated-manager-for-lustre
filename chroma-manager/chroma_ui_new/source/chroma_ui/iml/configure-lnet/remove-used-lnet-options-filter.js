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


angular.module('configure-lnet-module').filter('removeUsedLnetOptions', [function removeUsedLnetOptionsFilter () {
  'use strict';

  /**
   * This filter picks out currently selected lnd_network options
   * minus the current networkInterface and returns the altered list.
   * @param {Array} options The list of Lustre Network options.
   * @param {Array} networkInterfaces The list of network interfaces.
   * @param {Array} networkInterface The network interface bound to the current select.
   * @returns {Array} The filtered list of options.
   */
  return function (options, networkInterfaces, networkInterface) {
    var nids = _.chain(networkInterfaces)
      .without(networkInterface)
      .pluck('nid')
      .value();

    return options.filter(function removeOptions (option) {
      // Not Lustre Network is a special case.
      // It should always be included.
      if (option.value === -1)
        return true;

      return nids.every(function (nid) {
        return nid.lnd_network !== option.value;
      });
    });
  };
}]);
