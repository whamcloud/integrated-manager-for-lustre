/*jshint node: true*/
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
