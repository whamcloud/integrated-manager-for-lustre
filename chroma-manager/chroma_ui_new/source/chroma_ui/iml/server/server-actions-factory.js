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


angular.module('server').factory('serverActions', [function serverActionsFactory () {
  'use strict';

  function convertNonMultiJob (hosts) {
    /*jshint validthis: true */
    return [{
      class_name: this.jobClass,
      args: {
        hosts: hosts.map(function pluckResourceUri (host) {
          return host.resource_uri;
        })
      }
    }];
  }

  return [
    {
      value: 'Detect File Systems',
      message: 'Detecting File Systems',
      tooltip: 'detect_file_systems-tooltip',
      helpTopic: 'detect_file_systems-dialog',
      jobClass: 'DetectTargetsJob',
      convertToJob: convertNonMultiJob
    },
    {
      value: 'Re-write Target Configuration',
      message: 'Updating file system NIDs',
      tooltip: 'rewrite_target_configuration-tooltip',
      helpTopic: 'rewrite_target_configuration-dialog',
      jobClass: 'UpdateNidsJob',
      convertToJob: convertNonMultiJob,
      isDisabled: function isDisabled (host) {
        return !host.server_profile.managed;
      }
    },
    {
      value: 'Install Updates',
      message: 'Install updates',
      tooltip: 'install_updates_configuration-tooltip',
      helpTopic: 'install_updates_dialog',
      jobClass: 'UpdateJob',
      convertToJob: function convertToJob (hosts) {
        return hosts.map(function converter (host) {
          return {
            class_name: this.jobClass,
            args: {
              host_id: host.id
            }
          };
        }, this);
      },
      isDisabled: function isDisabled (host) {
        return host.member_of_active_filesystem && !host.immutable_state;
      }
    }
  ];
}]);
