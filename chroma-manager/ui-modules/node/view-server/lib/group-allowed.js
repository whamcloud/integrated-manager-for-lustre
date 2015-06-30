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

var λ = require('highland');
var groups = require('./groups');

module.exports = λ.curry(function groupAllowed (groupName, session) {
  var hasGroups = session && session.user && Array.isArray(session.user.groups);

  return hasGroups && session.user.groups.some(function some (group) {
    //Superusers can do everything.
    if (group.name === groups.SUPERUSERS) return true;

    //Filesystem administrators can do everything a filesystem user can do.
    if (group.name === groups.FS_ADMINS && groupName === groups.FS_USERS) return true;

    // Fallback to matching on names.
    return group.name === groupName;
  });
});
