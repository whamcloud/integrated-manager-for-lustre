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


'use strict';

/**
 * Adds methods to write from the spark.
 * @param {Function} errorSerializer
 * @param {Function} MultiplexSpark
 * @returns {Object}
 */
exports.wiretree = function primusServerWriteFactory (errorSerializer, MultiplexSpark) {
  return {
    /**
     * Add methods to write / end data in a predefined format.
     * Overrides MultiplexSpark as MultiplexSpark redefines Spark in it's plugin.
     */
    server: function server () {
      ['write', 'end'].forEach(function addMethodsToSpark (type) {
        MultiplexSpark.prototype[type + 'Response'] = generateResponseFunc(type);
        MultiplexSpark.prototype[type + 'Error'] = generateErrorFunc(type);
      });

      MultiplexSpark.prototype.getErrorFormat = function getErrorFormat (statusCode, error) {
        var message = {
          statusCode: statusCode,
          error: errorSerializer(error)
        };

        message.error.statusCode = statusCode;

        return message;
      };

      MultiplexSpark.prototype.getResponseFormat = function getResponseFormat (statusCode, response) {
        return {
          statusCode: statusCode,
          body: response
        };
      };

      /**
       * HOF that calls a type method on the spark
       * @param {String} type
       * @returns {Function}
       */
      function generateResponseFunc (type) {
        /**
         * Writes a response back to the client, possibly closes the connection.
         * @param {Number} statusCode The HTTP status code to send.
         * @param {Object} response The response to send.
         */
        return function responseFunc (statusCode, response) {
          this[type](this.getResponseFormat(statusCode, response));
        };
      }

      /**
       * HOF that calls a type method on the spark
       * @param {String} type
       * @returns {Function}
       */
      function generateErrorFunc (type) {
        /**
         * Writes an error back to the client, possibly closes the connection.
         * @param {Number} statusCode The HTTP status code to send.
         * @param {Error} error The error to serialize and send.
         */
        return function errorFunc (statusCode, error) {
          this[type](this.getErrorFormat(statusCode, error));
        };
      }
    }
  };
};
