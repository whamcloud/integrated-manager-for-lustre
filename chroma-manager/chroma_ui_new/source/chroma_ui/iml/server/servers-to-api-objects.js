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


angular.module('server').factory('serversToApiObjects', ['ADD_SERVER_AUTH_CHOICES',
  function serversToApiObjectsFactory (ADD_SERVER_AUTH_CHOICES) {
    'use strict';

    return function serversToApiObjects (servers) {
      var toPick = ['auth_type'];

      if (servers.auth_type === ADD_SERVER_AUTH_CHOICES.ROOT_PASSWORD)
        toPick.push('root_password');
      else if (servers.auth_type === ADD_SERVER_AUTH_CHOICES.ANOTHER_KEY)
        toPick.push('private_key', 'private_key_passphrase');

      var picked = _.pick(servers, toPick);
      return servers.addresses.map(function (address) {
        return _.extend({ address: address }, picked);
      });
    };
  }
]);
