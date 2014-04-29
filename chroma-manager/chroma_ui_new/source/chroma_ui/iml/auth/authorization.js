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


(function () {
  'use strict';

  angular.module('auth').service('authorization', ['sessionModelSingleton', Authorization]);

  function Authorization(sessionModelSingleton) {
    this.readEnabled = function readEnabled() {
      return sessionModelSingleton.$promise.then(function getSession(session) {
        return session.read_enabled;
      });
    };

    this.groupAllowed = function groupAllowed(groupName) {
      return sessionModelSingleton.$promise.then(function getSession(session) {
        var hasGroups = session.user && Array.isArray(session.user.groups);

        return hasGroups && session.user.groups.some(function some(group) {
          //Superusers can do everything.
          if (group.name === GROUPS.SUPERUSERS) return true;

          //Filesystem administrators can do everything a filesystem user can do.
          if (group.name === GROUPS.FS_ADMINS && groupName === GROUPS.FS_USERS) return true;

          // Fallback to matching on names.
          return group.name === groupName;
        });
      });
    };
  }

  var GROUPS = Object.freeze({
    SUPERUSERS: 'superusers',
    FS_ADMINS: 'filesystem_administrators',
    FS_USERS: 'filesystem_users'
  });

  angular.module('auth').constant('GROUPS', GROUPS);

  angular.module('auth').directive('restrictTo', ['authorization', function (authorization) {
    return {
      link: function ($scope, el, attrs) {
        authorization.groupAllowed(attrs.restrictTo).then(function then (allowed) {
          if (!allowed)
            el.addClass('invisible');
        });
      }
    };
  }]);
}());