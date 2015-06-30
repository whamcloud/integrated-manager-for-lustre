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

var getDirTreeSync = require('./get-dir-tree-sync');
var _ = require('lodash-mixins');
var conf = require('../conf');

var templates = getDirTreeSync(conf.templateRoot, transformPath);

_.templateSettings.imports = {
  _: _,
  t: function t (name, data) {
    return templates[name](data);
  },
  conf: conf,
  getServerDate: function getServerDate () {
    return new Date();
  }
};

_.templateSettings.interpolate =  /<\$=([\s\S]+?)\$>/g;
_.templateSettings.escape =  /<\$-([\s\S]+?)\$>/g;
_.templateSettings.evaluate =  /<\$([\s\S]+?)\$>/g;

templates = _.transform(templates, function (result, value, key) {
  result[key] = _.template(value);
});

module.exports = templates;

/**
 * Remove extra leading path from template
 * @param {String} p
 * @returns {String}
 */
function transformPath (p) {
  return p.replace(conf.templateRoot, '');
}
