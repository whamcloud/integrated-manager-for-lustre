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


angular.module('app').controller('AppCtrl',
  ['$routeSegment', 'SessionModel', 'navigate', 'ENV', 'GROUPS', 'help', AppCtrl]);

function AppCtrl ($routeSegment, SessionModel, navigate, ENV, GROUPS, help) {
  'use strict';

  var self = this;

  this.$routeSegment = $routeSegment;

  this.RUNTIME_VERSION = ENV.RUNTIME_VERSION;

  this.COPYRIGHT_YEAR = help.get('copyright_year');

  this.GROUPS = GROUPS;

  SessionModel.get().$promise.then(function (resp) {
    self.session = resp;
    self.user = resp.user;
    self.loggedIn = self.user.id != null;
    self.onClick = (self.loggedIn ? self.logout : self.login);
  });

  this.isCollapsed = true;

  this.login = function login() {
    navigate('login/');
  };

  this.logout = function logout() {
    self.session.$delete().then(self.login);
  };
}
