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


'use strict';

var inherits = require('util').inherits,
  url = require('url'),
  _ = require('lodash');

module.exports = function ostBalanceDataSourceFactory(conf, request, logger, BaseDataSource) {
  function OstBalanceDataSource(name) {
    BaseDataSource.call(this, conf, request, logger, name);
  }

  inherits(OstBalanceDataSource, BaseDataSource);

  OstBalanceDataSource.prototype.beforeSend = function (options) {
    var percentage = options.query.percentage,
    query = {
      kind: 'OST',
      metrics: 'kbytestotal,kbytesfree',
      latest: true
    };

    if (percentage != null) query.percentage = percentage;

    this.logger.info({queryString: query}, 'Query string passed');

    return {
      url: url.resolve(this.url, 'target/metric/'),
      qs: query
    };
  };

  OstBalanceDataSource.prototype.transformData = function(data, done) {
    var self = this;

    this.request({
      url: url.resolve(this.url, 'target/'),
      qs: {
        kind: 'OST',
        limit: 0
      }
    }, callback);

    function callback(err, resp, body) {
      if (err) {
        self.emit('error', {error: err});
        return;
      } else if (resp.statusCode >= 400) {
        self.emit('error', {error: body, statusCode: 400});
        return;
      }

      var objects = body.objects;

      var dataJoinedWithTargets = Object.keys(data).reduce(function (obj, key) {
        var record = _.find(objects, {id: key});

        if (record)
          obj[record.name] = data[key];
        else
          obj[key] = data[key];

        return obj;
      }, {});

      done(dataJoinedWithTargets);
    }
  };

  return function getInstance(name) {
    return new OstBalanceDataSource(name);
  };
};