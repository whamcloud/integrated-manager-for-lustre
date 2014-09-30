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


angular.module('server')
  .factory('createOrUpdateHostsThen', ['$q', 'requestSocket', 'throwResponseError',
    'serversToApiObjects', 'CACHE_INITIAL_DATA',
  function createOrUpdateHostsThenFactory ($q, requestSocket, throwResponseError,
                                           serversToApiObjects, CACHE_INITIAL_DATA) {
    'use strict';

    var defaultProfileResourceUri = _.find(CACHE_INITIAL_DATA.server_profile, { name: 'default' }).resource_uri;

    /**
     * Creates or updates hosts as needed.
     * @param {Object} servers
     * @param {Object} serverSpark
     * @returns {Object} A promise.
     */
    return function createOrUpdateHostsThen (servers, serverSpark) {
      var objects = serversToApiObjects(servers);
      var spark = requestSocket();

      return serverSpark.onceValueThen('data')
        .catch(throwResponseError)
        .then(_.pluckPath('body.objects'))
        .then(function handleResponse (servers) {
          var findByAddress = _.findInCollection(['address']);

          var toPost = objects
            .filter(_.compose(_.inverse, findByAddress(servers)))
            .map(function addDefaultProfile (object) {
              object.server_profile = defaultProfileResourceUri;
              return object;
            });

          var toPostPromise = hostWorkerThen(spark, 'sendPost', toPost);

          var undeployedServers = _.where(servers, { state: 'undeployed' });
          var toPut = _.difference(objects, toPost)
            .filter(findByAddress(undeployedServers));

          var toPutPromise = hostWorkerThen(spark, 'sendPut', toPut);

          var leftovers = _.difference(objects, toPut, toPost);
          var unchangedServers = {
            body: {
              objects: servers
                .filter(findByAddress(leftovers))
                .map(function buildResponse (server) {
                  return {
                    command_and_host: {
                      command: false,
                      host: server
                    },
                    error: null,
                    traceback: null
                  };
                })
            }
          };

          //@TODO: Switch to allSettled once
          //we are on 1.3.x and $q is prototype
          //based and can be extended.
          return $q.all([toPostPromise, toPutPromise])
            .then(function combineResponses (responses) {
              responses = responses
                .concat(unchangedServers)
                .concat(function concatArrays (a, b) {
                  return Array.isArray(a) ? a.concat(b) : undefined;
                });

              return _.merge.apply(_, responses);
            });
      })
        .finally(function endSpark () {
          spark.end();
        });
    };

    /**
     * Creates or updates servers.
     * @param {Object} spark
     * @param {String} method
     * @param {Object} data
     * @returns {Object} A promise.
     */
    function hostWorkerThen (spark, method, data) {
      if (data.length === 0)
        return $q.when({});

      return spark[method]('/host', {
        json: { objects: data }
      }, true)
        .catch(function throwError (response) {
          throw response.error;
        });
    }
  }
]);
