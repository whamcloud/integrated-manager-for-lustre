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


angular.module('dashboard').service('dashboardPath', ['$routeSegment', function DashboardPath ($routeSegment) {
  'use strict';

  var FS = 'fs';
  var FS_LABEL = 'file system';
  var SERVER = 'server';
  var OST = 'ost';
  var MDT = 'mdt';
  var BASE_PATH = 'dashboard';

  /**
   * The base dashboard path.
   * @type {string}
   */
  this.basePath = BASE_PATH;

  /**
   * Checks if the route points at the dashboard.
   * @returns {Boolean}
   */
  this.isDashboard = function isDashboard () {
    return $routeSegment.contains(BASE_PATH);
  };

  /**
   * Checks if the route points at the base dashboard.
   * @returns {Boolean}
   */
  this.isBase = function isBase () {
    return $routeSegment.contains('base');
  };

  /**
   * Checks if the route points to a fs.
   * @returns {boolean}
   */
  this.isFs = function isFs() {
    return $routeSegment.$routeParams.fsId != null;
  };

  /**
   * Checks if the route points to a server.
   * @returns {boolean}
   */
  this.isServer = function isServer () {
    return $routeSegment.$routeParams.serverId != null;
  };

  /**
   * Checks if the route points to a fs or server.
   * @returns {Boolean}
   */
  this.isType = function isType () {
    return this.isFs() || this.isServer();
  };

  /**
   * Checks if the route points to an OST.
   * @returns {Boolean}
   */
  this.isOst = function isOst () {
    return $routeSegment.contains(OST);
  };

  /**
   * Checks if the route points to a MDT.
   * @returns {Boolean}
   */
  this.isMdt = function isMdt () {
    return $routeSegment.contains(MDT);
  };

  /**
   * Checks if the route points to an OST or MDT.
   * @returns {Boolean}
   */
  this.isTarget = function isTarget () {
    return this.isOst() || this.isMdt();
  };

  /**
   * Returns the fs id.
   * @returns {string}
   */
  this.getFsId = function getFsId () {
    return $routeSegment.$routeParams.fsId;
  };

  /**
   * Returns the server id.
   * @returns {string}
   */
  this.getServerId = function getServerId () {
    return $routeSegment.$routeParams.serverId;
  };

  /**
   * Returns the OST or MDT id.
   * @returns {string|undefined}
   */
  this.getTargetId = function getTargetId () {
    if (this.isOst())
      return $routeSegment.$routeParams.ostId;

    if (this.isMdt())
      return $routeSegment.$routeParams.mdtId;
  };

  /**
   * Returns the target name.
   * @returns {string|undefined}
   */
  this.getTargetName = function getTargetName () {
    if (this.isOst())
      return OST;

    if (this.isMdt())
      return MDT;
  };

  /**
   * Returns the fs or server id.
   * @returns {string|undefined}
   */
  this.getTypeId = function getTypeId () {
    if (this.isFs())
      return this.getFsId();

    if (this.isServer())
      return this.getServerId();
  };

  /**
   * Returns the name of the type.
   * @returns {string|undefined}
   */
  this.getTypeName = function getTypeName() {
    if (this.isFs())
      return FS;

    if (this.isServer())
      return SERVER;
  };

  /**
   * Returns the label for the current type.
   * @returns {string|undefined}
   */
  this.getTypeLabel = function getTypeLabel() {
    if (this.isFs())
      return FS_LABEL;

    if (this.isServer())
      return SERVER;
  };

  /**
   * Get the path to the current type
   * @returns {String}
   */
  this.getTypePath = function getTypePath () {
    var params = {
      type: {
        name: this.getTypeName(),
        id: this.getTypeId()
      }
    };

    return this.buildPath(params);
  };

  /**
   * Builds out the path.
   * @param {object} [params] If provided, used to build path. Otherwise falls back to deriving path.
   * @returns {String}
   */
  this.buildPath = function buildPath (params) {
    var path = [BASE_PATH];

    if (_.isPlainObject(params)) {
      if ('type' in params)
        path.push(params.type.name, params.type.id);

      if ('target' in params)
        path.push(params.target.name, params.target.id);
    } else {
      if (this.isType())
        path.push(
          this.getTypeName(),
          this.getTypeId()
        );

      if (this.isTarget())
        path.push(
          this.getTargetName(),
          this.getTargetId()
        );
    }

    return path.reduce(function (str, arg) {
      return (str += arg + '/');
    }, '');
  };
}]);