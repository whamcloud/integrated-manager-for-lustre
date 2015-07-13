//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


angular.module('server').factory('getTestHostSparkThen', ['throwIfServerErrors', 'throwResponseError', 'throwIfError',
  function getTestHostSparkThenFactory (throwIfServerErrors, throwResponseError, throwIfError) {
    'use strict';

    /**
     * Tests host with provided data.
     * Keeps asking about the server's status.
     * Returns a promise containing the spark.
     * @param {Function} flint Creates sparks.
     * @param {Object} objects The data to send.
     * @returns {Object} A promise
     */
    return function getTestHostSparkThen (flint, objects) {
      var spark = flint('testHost');

      spark.sendPost('/test_host', {
        json: objects
      });

      return spark
        .addPipe(throwIfError(throwIfServerErrors(_.identity)))
        .addPipe(_.unwrapResponse(_.fmap(function (server) {
          server.status.forEach(function (status) {
            status.uiName = _.apiToHuman(status.name);
          });

          return server;
        })))
        .addPipe(function checkTotalValidity (response) {
          response.body.valid = _.every(response.body.objects, 'valid');
          return response;
        })
        .onceValueThen('pipeline')
        .catch(throwResponseError)
        .then(function resolveWithSpark () {
          return spark;
        });
    };
  }
]);
