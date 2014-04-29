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


angular.module('configureLnet').factory('NetworkInterface',
  ['baseModel', 'LNET_OPTIONS', 'Nids', function (baseModel, LNET_OPTIONS, Nids) {
  'use strict';

  var NetworkInterface = baseModel({
    url: '/api/network_interface/:networkId',
    params: { networkId: '@id' },
    actions: {
      query: {
        interceptor: {
          response: function (resp) {
            resp.resource.forEach(function (resource) {
              if (!resource.nid)
                resource.nid = {
                  lnd_network: LNET_OPTIONS[0].value,
                  network_interface: resource.resource_uri
                };
            });

            return resp.resource;
          }
        }
      }
    }
  });

  /**
   * Updates each nid individually and returns a promise representing the completion of all of them.
   * @static
   * @param {Array.NetworkInterface} networkInterfaces a collection of network interfaces.
   * @returns {Object} A promise representing all the nid updates.
   */
  NetworkInterface.updateInterfaces = function updateInterfaces(networkInterfaces) {
    var updates = networkInterfaces.map(function (networkInterface) {
      return networkInterface.nid;
    });

    var nids = new Nids({objects: updates});

    return nids.$save();
  };

  return NetworkInterface;
}])

.factory('Nids', ['baseModel', function (baseModel) {
  'use strict';

  return baseModel({
    url: '/api/nid/'
  });
}]);
