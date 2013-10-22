//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
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


(function () {
  'use strict';

  /**
   * Responsible for setting up bi-directional middleware routes between protocol and the model.
   * @param {object} $q
   * @param {object} $parse
   * @param {object} protocol
   * @param {object} [middlewares]
   * @constructor
   */
  function Persist($q, $parse, protocol, middlewares) {
    this._$q = $q;
    this._$parse = $parse;
    this.protocol = protocol;
    this.lastProtocolChange = undefined;

    middlewares = _.clone(middlewares) || {};
    middlewares.modelChange = [].concat(middlewares.modelChange || [], this.protocol.process);
    middlewares.protocolChange = [].concat(middlewares.protocolChange || [],
      function (newVal, oldVal, deferred) {
        this.lastProtocolChange = newVal;
        deferred.resolve(newVal);
      },
      function (newVal, oldVal, deferred) {
        angular.copy(newVal, this.getter());

        deferred.resolve(newVal);
      }
    );

    this.modelChangeMiddlewares = this.generateMiddlewareProcessor(middlewares.modelChange);
    this.protocolChangeMiddlewares = this.generateMiddlewareProcessor(middlewares.protocolChange);
  }

  /**
   * Binds a scope to a protocol.
   * @param {object} $scope
   * @param {string|function} expression
   */
  Persist.prototype.assign = function ($scope, expression) {
    var self = this,
      parsed = this._$parse(expression);

    this.getter = parsed.bind(null, $scope);
    this.setter = parsed.assign.bind(null, $scope);

    this.protocol.subscribe(this);

    $scope.$watch(expression, function (newVal, oldVal) {
      //Nothing changed, return early.
      if(angular.equals(newVal, self.lastProtocolChange)) return;

      self.modelChangeMiddlewares(newVal, oldVal);
    }, true);

    $scope.$on('$destroy', this.unassign.bind(this));
  };

  /**
   * Removes existing bindings
   * @throws {error} if nothing is bound.
   */
  Persist.prototype.unassign = function () {
    this.protocol.unsubscribe();
    this.setter = null;
    this.getter = null;
  };

  /**
   * given a queue of middleware returns a function that when called recursively iterates the list.
   * @param {array} queue
   *
   * @returns function
   */
  Persist.prototype.generateMiddlewareProcessor = function (queue) {
    var $q = this._$q;

    queue = queue.map(function (middleware) { return middleware.bind(this); }, this);

    return function processMiddleware(newVal, oldVal, index) {
      index = (index == null ? 0 : index);

      if (index === queue.length) return;

      var deferred = $q.defer();

      queue[index](newVal, oldVal, deferred);

      index += 1;

      deferred.promise.then(function (data) { processMiddleware(data, oldVal, index); });
    };
  };

  Persist.prototype.protocolChange = function (promise) {
    var self = this;

    promise.then(function (newVal) {
      self.protocolChangeMiddlewares(newVal, self.lastProtocolChange);
    });
  };

  angular.module('persist').factory('persist', ['$q', '$parse', function ($q, $parse) {
    return function (protocol, middlewares) {
      return new Persist($q, $parse, protocol, middlewares);
    };
  }]);
}());
