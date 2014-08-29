/*jshint node: true*/
'use strict';

/**
 * The request router
 * @param {Object} config
 * @param {Function} dynamicRequest
 * @param {Object} routes
 * @param {Logger} logger
 * @returns {Function}
 */
exports.wiretree = function routerModule(config, dynamicRequest, routes, logger) {
  /**
   * Routes the request appropriately. If the pathname exists in the routes list in the config file then
   * the appropriate handler will be executed. Otherwise, the request will be delegated to the dynamic
   * request processor, which will return a RequestEntry object.
   * @param {String} pathname
   * @param {models.Request} request
   * @param {Object} body
   * @returns {Object | models.RequestEntry}
   */
  return function route(pathname, request, body) {
    // Gate check 1
    if (!pathname) {
      logger.warn('pathname was never passed to the router');

      return {
        status: config.status.NOT_FOUND
      };
    }

    // Gate check 2
    if (request == null) {
      logger.warn('request was never passed to the router');

      return {
        status: config.status.BAD_REQUEST
      };
    }

    // load the appropriate module based on the pathname
    if (routes.restRoutes[pathname]) {
      logger.info('routing to ' + pathname);
      return routes.restRoutes[pathname](request, body);
    } else {
      // Making a dynamic call to an entry that has been registered.
      logger.info('making dynamic request');
      return dynamicRequest(request, body);
    }
  };
};
