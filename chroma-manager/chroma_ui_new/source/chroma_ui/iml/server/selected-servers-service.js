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


angular.module('server').service('selectedServers', [function SelectedServersService () {
  'use strict';

  var selectedServers = this;

  this.servers = {};

  /**
   * Toggles the server according to the specified type.
   * @param {String} name
   */
  this.toggleType = function toggleType (name) {
    var checked;

    if (name === 'all')
      checked = function handleCheckedAll (key) {
        selectedServers.servers[key] = true;
      };
    else if (name === 'none')
      checked = function handleCheckedNone (key) {
        selectedServers.servers[key] = false;
      };
    else if (name === 'invert')
      checked = function handleCheckedInvert (key) {
        selectedServers.servers[key] = !selectedServers.servers[key];
      };

    Object.keys(selectedServers.servers).forEach(checked);
  };

  /**
   * Given an array of servers, adds them to the selectedServers array
   * if they don't already exist.
   * @param {Array} servers
   */
  this.addNewServers = function addNewServers (servers) {
    servers.forEach(function addThem (server) {
      if (selectedServers.servers[server.fqdn] == null)
        selectedServers.servers[server.fqdn] = false;
    });
  };
}]);
