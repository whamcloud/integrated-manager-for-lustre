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

'use strict';

exports.wiretree = function configModule(configulator) {
  var config = {
    default: {
      status: {
        SUCCESS: 200,
        CREATED: 201,
        BAD_REQUEST: 400,
        NOT_FOUND: 404,
        INTERNAL_SERVER_ERROR: 500
      },
      methods: {
        GET: 'GET',
        PUT: 'PUT',
        POST: 'POST',
        DELETE: 'DELETE',
        PATCH: 'PATCH'
      },
      standardHeaders: {
        'Content-Type': 'application/json'
      },
      requestUrls: {
        MOCK_REQUEST: '/api/mock',
        MOCK_STATE: '/api/mockstate',
        MOCK_LIST: '/api/mocklist'
      },
      port: 8888,
      logName: 'stubdaddy',
      get isProd() {
        return process.env.NODE_ENV === 'production';
      },
      logger: {
        logPath: '',
        level: 'debug',
        streams: ['stdout','file']
      },
      requestProtocol: 'https'
    },
    development: {
      logger: {
        logPath: '',
        level: 'debug',
        streams: ['file']
      }
    },
    test:{
      logger: {
        logPath: '',
        level: 'debug',
        streams: ['file']
      }
    },
    production: {
      logger: {
        logPath: '',
        level: 'info',
        streams: ['file']
      }
    }
  };

  return configulator(config);
};
