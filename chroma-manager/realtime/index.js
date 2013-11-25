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

var domain = require('domain'),
  d = domain.create();

d.on('error', function(err) {
  console.log(err);

  process.exit(1);
});

d.run(function initialize() {
  var https = require('https'),
    di = require('di'),
    nodeRequest = require('request'),
    serverFactory = require('./server'),
    request = require('./request'),
    logger = require('./logger'),
    BaseDataSource = require('./data-sources/base-data-source'),
    conf = require('./conf'),
    primus = require('./primus'),
    Primus = require('primus'),
    multiplex = require('primus-multiplex'),
    metricsModel = require('./models/metrics-model'),
    metricsDataSources = require('./data-sources/metrics');

  var modules = [{
    conf: ['value', conf],
    https: ['value', https],
    BaseDataSource: ['value', BaseDataSource],
    nodeRequest: ['value', nodeRequest],
    request: ['factory', request],
    server: ['factory', serverFactory],
    logger: ['value', logger],
    Primus: ['value', Primus],
    multiplex: ['value', multiplex],
    primus: ['factory', primus],
    metricsModel: ['factory', metricsModel.metricsModelFactory],
    MetricsDataSource: ['factory', metricsDataSources.getMetricsDataSource],
    mdtDataSourceFactory: ['factory', metricsDataSources.mdtDataSourceFactory],
    mdsDataSourceFactory: ['factory', metricsDataSources.mdsDataSourceFactory],
    ostBalanceDataSourceFactory: ['factory', metricsDataSources.ostBalanceDataSourceFactory]
  }];

  var injector = new di.Injector(modules);

  injector.invoke(function (logger, metricsModel,
                            mdtDataSourceFactory, mdsDataSourceFactory, ostBalanceDataSourceFactory) {

    logger.info('Realtime Module started.');

    metricsModel('mds', mdsDataSourceFactory);
    metricsModel('ostbalance', ostBalanceDataSourceFactory);
    metricsModel('mdt', mdtDataSourceFactory);
  });
});
