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


var TextUpdaterModel = function(options) {

  var self;

  /* update is the only method called by the TextUpdater to update the data
   * - it can be overridden to do your own custom updates
   * - by default it will iterate throug the keys of the data, do a lookup via render_to
   */
  function update(snapshot_data) {
    _.each( snapshot_data, function(value, key) {
      if ( _.has(self.render_to, key) ) {
        $(self.render_to[key]).text(value);
      }
    });
  };

  self = $.extend(true, {
    api_params: {},             // the static params sent to the api request (excluding metrics)
    api_params_callback: null,
    consumer_group: '',         // the consumer group. Analagous to the tab and/or page, formerly chart_group
    enabled: true,              // you can disable an updater by setting this to false
    metrics: [],                // list of metrics to get
    snapshot_data: null,        //
    render_to: {},              // the simple anon object that maps snapshot_data keys to jquery selectors
    state: 'idle',              // 'idle', 'loading'
    update: update,             // overriderable function to update the data for this model
    url: '',                    // url (str or func for dynamic) of the metric api to get

    // the callback that processes the snapshot data and returns an anonymous object with keys of data
    // base case just returns the first objects data -- override for more complex
    snapshot_callback: function (consumer, snapshot_data) {
      return snapshot_data.length ? snapshot_data[0].data : {};
    }
  }, options || {});

  return self;

};



var TextUpdater = function(options) {
  var config = $.extend(true, {
    consumers: {}, // formerly charts
    consumer_group: '', //formerly chart_group
    debug: false,
    default_time_boundary: 5 * 60 * 1000,
    interval_id: null,
    interval_seconds: 10
  }, options || {});

  config.consumers[config.consumer_group] = {};

  // getter/setter for currently active consumer group
  var consumer_group = function(group) {
    if (_.isUndefined(group)) {
      return config.consumer_group;
    }

    if (_.isUndefined(config.consumers[group])) {
      config.consumers[group] = {};
    }
    config.consumer_group = group;
  };

  // Logger, only goes to console if debug is true
  var log = function(msg) {
    if (config.debug && _.isString(msg)) {
      console.log(msg);
    }
  };

  // accessor/mutator for debug
  var debug = function(value) {
    if (_.isUndefined(value)) {
      return config.debug;
    } else if (_.isBoolean(value)) {
      config.debug = value;
      return value;
    } else {
      log("debug must be a bool");
    }
  };

  // add a data consumer from a model
  var add_consumer = function(consumer_name, consumer_group, options) {
    if (!_.isString(consumer_name) || ! consumer_name.length ) {
      log("consumer_name must be a non-empty string: " + consumer_name);
      return;
    }
    if (!_.isString(consumer_group)) {
      log("consumer_group must be a non-empty string: " + consumer_group);
      return;
    }
    log("add_consumer: " + consumer_name)
    config.consumers[consumer_group][consumer_name] = TextUpdaterModel(options || {});
  };

  // does an update cycle of all consumers in currently active group
  var render = function() {
    log('render consumers');
    _.each(config.consumers[config.consumer_group], function(consumer, key) {
      if (consumer.enabled && consumer.state == 'idle') {
        log('- rendering consumer ' + key);
        update(consumer);
      }
    });
  };

  function update(consumer) {
    var api_params = $.extend(true, {}, consumer.api_params);
    api_params = default_params(api_params, consumer);
    // custom params
    if (_.isFunction(consumer.api_params_callback)) {
      api_params = consumer.api_params_callback(api_params, consumer);
    }

    consumer.state = 'loading';
    var url= _.isFunction(consumer.url) ? consumer.url() : consumer.url;
    Api.get(
      url,
      api_params,
      success_callback = function(data) {
        consumer.state = 'idle';
        // all text updates are snapshots
        //snapshot_callback should return snapshot_data
        consumer.update( consumer.snapshot_callback(consumer,data) );
      },
      error_callback = {
        404: function(status, jqXHR) {
          var markup = "<div style='overflow-y: auto; max-height: 700px;'>This resource has gone away.  Return to front page.</div>";
          $(markup).dialog({
            'buttons': {
              'Return': function() {
                $(this).dialog('close');
                window.location.href = Api.UI_ROOT;
              }
            }
          });
        }
      },
      false
    );
  }

  // default parameters that must always go in
  var default_params = function(api_params, consumer) {
    var params = {
      metrics: consumer.metrics.join(","),
      latest: true //always a snapshot for text updater
    };
    return $.extend(true, api_params, params);
  };

  var init = function() {
    if (_.has(config.consumers,config.consumer_group) ) {
      render();
      if (config.interval_seconds > 0) {
        config.interval_id = setInterval(render, config.interval_seconds * 1000);
      }
    }
  };

  // Interval based refreshing
  var clear_recurring = function() {
    if (_.isNumber(config.interval_id)) {
      clearInterval(config.interval_id);
    }
    config.interval_id = null;
    config.interval_seconds = 0;
  };
  var set_recurring = function(seconds) {
    if (!_.isNumber(seconds)) {
      log("set_recurring(seconds) must be a number");
      return;
    }
    if (!_.isNull(config.interval_id)) {
      clearInterval(config.interval_id);
    }
    config.interval_id = setInterval(render, seconds * 1000);
    config.interval_seconds = seconds;
  };

  var destroy = function() {
    clear_recurring();
  };

  // return an object
  return {
    add_consumer: add_consumer,
    consumer_group: consumer_group,
    clear_recurring: clear_recurring,
    config: config,
    destroy: destroy,
    init: init,
    render: render,
    set_recurring: set_recurring,
    log: log
  };
}