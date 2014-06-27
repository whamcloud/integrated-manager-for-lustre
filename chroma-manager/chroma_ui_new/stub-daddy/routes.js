/*jshint node: true*/
'use strict';

exports.wiretree = function routesModule(registerApi, mockState) {
  return Object.freeze({
    restRoutes: {
      '/api/mock': registerApi,
      '/api/mockstate': mockState
    }
  });
};
