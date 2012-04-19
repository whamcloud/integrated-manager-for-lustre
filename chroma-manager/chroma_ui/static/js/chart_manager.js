//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

/*************************
 * Dependancies:
 * - VENDOR
 *     - jquery
 *     - underscore
 *     - highcharts
 * - LIBS
 *     - api.js
 * - GLOBALS
 *     - ChartModel -- Generator for a chart object
 *     - ChartManager - Generator for a chart manager object
 *     - chart_manager - Global instance of the ChartManager
 */
function dump(arr,level) {
  var dumped_text = "";
  if(!level) level = 0;
  
  //The padding given at the beginning of the line.
  var level_padding = "";
  for(var j=0;j<level+1;j++) level_padding += "    ";
  
  if(typeof(arr) == 'object') { //Array/Hashes/Objects 
    for(var item in arr) {
      var value = arr[item];
      
      if(typeof(value) == 'object') { //If it is an array,
        dumped_text += level_padding + "'" + item + "' ...\n";
        dumped_text += dump(value,level+1);
      } else {
        dumped_text += level_padding + "'" + item + "' => \"" + value + "\"\n";
      }
    }
  } else { //Strings/Chars/Numbers etc.
    dumped_text = "===>"+arr+"<===("+typeof(arr)+")";
  }
  return dumped_text;
}
var ChartModel = function(options) {

    var config = $.extend(true,  {
        api_params              : {},   // the static params sent to the api request (excluding metrics)
        api_params_callback     : null,
        chart_config            : {},   // highcharts config
        chart_config_callback   : null, // callback to modify chart config
        chart_group             : '',   // the chart group. Analagous to the tab
        enabled                 : true, // you can disable a graph by setting this to false
        error_callback          : null, // a callback executed on an error conditoin (not needed really, but an option)
        instance                : null, // stores the highcharts instance
        is_zoom                 : false, // whether we have a zoomed graph
        metrics                 : [],    // list of metrics to get
        prep_params             : null,  // callback for custom dynamic paramaters to send to the api
        snapshot                : false, // if true, displays latest data rather than time series
        series_begin            : null,  // Date object representing beginning of series
        series_end              : null,  // date object representing end of series
        series_data             : [],    // stores all series data here and updates to here
        series_id_to_index      : {},    // map our series key to highchart's index for the series
        series_callbacks        : null,    // list of callbacks for each series
        state                   : 'idle', // 'idle', 'loading'
        url                     : ''     // url (str or func for dynamic) of the metric api to get
    }, options || {});

    if( config.is_zoom ) {
        $.extend(true,config.api_params, {
            xAxis: { labels: { style: { fontSize: '12px'} } },
            yAxis: { labels: { style: { fontSize: '12px', fontWeight: 'bold' } } },
            chart: {
                width: 780,
                height: 360,
                style: { height: 360, width: "100%" }
            },
            legend: { enabled: true }
        });
    }
    
    config.reset_series = function() {
        config.series_data = [];
        _.each(config.chart_config.series, function() { config.series_data.push([]); } );
    };

    config.reset_series();        
    return config;

};

var ChartManager = function(options) {
  var config = $.extend(true, {
        charts: {},
        chart_group: '',
        chart_config_defaults: {
          chart: {
            animation: false,
            zoomType: 'xy',
            backgroundColor: '#f9f9ff'
          },
          credits: {
            enabled: false
          },
          title: {style: { fontSize: '12px' } },
          legend: { enabled: false},
          plotOptions: {
            line: {
                    lineWidth: 2,
                    marker: {enabled: false},
                    shadow: false
                  },
            series:{marker: {enabled: false}},
            column:{ pointPadding: 0.0, shadow: false, groupPadding: 0.0, borderWidth: 0.0 },
            areaspline: {fillOpacity: 0.5},
            pie: { 
              allowPointSelect: true, cursor: 'pointer', showInLegend: true, size: '100%', 
              dataLabels: {
                enabled: false,
                color: '#000000',
                connectorColor: '#000000'
              }
            },
            area: {
              stacking: 'normal',
              lineColor: '#666666',
              lineWidth: 1,
              marker: {
                lineWidth: 1,
                lineColor: '#666666'
              }
            }
          }
        },
        debug: false,
        default_time_boundary: 5 * 60 * 1000,
        interval_id: null,
        interval_seconds: 10
    }, options || {});

    config.charts[config.chart_group] = {};

    var chart_group = function(group) {
        if (_.isUndefined(group)) {
            return config.chart_group;
        }
        else {
            if (_.isUndefined( config.charts[group]))
                config.charts[group] = {};
            config.chart_group = group;
        }
    };

    // Logger, only goes to console if debug is true
    var log = function(msg) {
        if ( config.debug && _.isString(msg) ) {
            console.log(msg);
        }
    };

    // accessor/mutator for debug
    var debug = function(value) {
        if ( _.isUndefined(value) ) { return config.debug; }
        else if ( _.isBoolean(value) ) { config.debug = value; return value; }
        else { log("debug must be a bool"); }
    };

    // add a chart from a chart model
    var add_chart = function(chart_name,chart_group,options) {
        if (! _.isString(chart_name) || chart_name.length < 1 ) {
            log("chart_name must be a non-empty string: " + chart_name);
            return;
        }
        if (! _.isString(chart_group) ) {
            log("chart_group must be a non-empty string: " + chart_name);
            return;
        }
        log("add_chart: " + chart_name)
        chart_model = ChartModel(options || {});
        config.charts[chart_group][chart_name] = ChartModel(options || {});
    };

    var render_charts = function() {
        log('render_charts');
        _.each(config.charts[config.chart_group], function(chart,key) {
            if (chart.enabled && chart.state == 'idle') {
                log('- rendering chart ' + key);
                update_chart(chart);
            }
        });
    };

    var default_params = function(api_params,chart) {
        var params = { metrics: chart.metrics.join(",") };
        if (chart.snapshot) {
          params.latest = true;
        }
        if ( _.isNull( chart.series_begin) ) {
            chart.series_end          = new Date();
            chart.series_begin        = new Date( chart.series_end - config.default_time_boundary );
        } else {
            if (!chart.snapshot) {
              params.update = 'true';
            }
        }
        params.begin = chart.series_begin.toISOString();
        params.end   = chart.series_end.toISOString();

        return $.extend(true, api_params, params );
    };

    var update_chart = function(chart) {
        if (_.isNull(chart.instance)) {
          var chart_config = 
              $.extend(true, {}, config.chart_config_defaults, chart.chart_config, {
                  // maps all the series data into single object literals with "data" as it's key
                  // this is to allow us to merge it into the config seamlessly
                  series: _.map(
                              chart.series_data,
                              function(series_data, i) { return { data: series_data }; }
                          )
          });
          if ( _.isFunction(chart.chart_config_callback)) {
            chart_config = chart.chart_config_callback(chart_config);
          }
          var container = $('#' + chart_config.chart.renderTo);
          if (container.prev('div.magni').length == 0) {
            container.before("<div class='magni'><button class='magbutton'></button></div>");
            container.prev('div.magni').find('button.magbutton').button({icons: {primary: 'ui-icon-zoomin'}});
            container.prev('div.magni').find('button.magbutton').click(function(ev) {
              var dialog = $("<div><div class='zoomed_chart'></div></div>");
              dialog.dialog({width: window.innerWidth - 200, height: 450, modal: true});
              var zoomed_container = dialog.find('.zoomed_chart');
              var zoomed_config = $.extend(true, {}, chart_config);
              zoomed_config.chart.renderTo = zoomed_container.get(0);

              var zoomed_chart = new ChartModel($.extend(true, {}, chart));
              zoomed_chart.instance = new Highcharts.Chart(zoomed_config);
              zoomed_chart.instance.showLoading();
              zoomed_chart.series_begin = null;

              update_chart_data(zoomed_chart);
            });
          }

          chart.instance = new Highcharts.Chart(chart_config);
          chart.instance.showLoading();
        }

      update_chart_data(chart);
    };

    function update_chart_data(chart) {
      var api_params = $.extend(true, {}, chart.api_params);
      api_params = default_params(api_params, chart);
      // custom params
      if ( _.isFunction(chart.api_params_callback) ) {
        api_params = chart.api_params_callback(api_params, chart);
      }

      chart.state = 'loading';
      var url;
      if ( _.isFunction(chart.url) ) {
        url = chart.url();
      } else {
        url = chart.url;
      }
      Api.get(
        url,
        api_params,
        success_callback = function(data) {
          chart.state = 'idle';
          if ( _.isObject(chart.instance) )
            chart.instance.hideLoading();

          if (chart.snapshot) {
            // Latest-value chart
            chart.reset_series();
            chart.snapshot_callback(chart, data);
          } else {
            // Time series chart
            if (chart.data_callback) {
              // If data_callback is provided, it will update series_data for us
              var series_updates = chart.data_callback(chart, data);
              _.each(series_updates, function(series_update, series_id) {
                if (chart.series_id_to_index[series_id] == undefined) {
                  var series_conf = $.extend(true, {}, chart.series_template, {name: series_update.label})
                  var added_series = chart.instance.addSeries(series_conf);
                  chart.series_id_to_index[series_id] = added_series.index;
                  chart.series_data[added_series.index] = []
                }

                var i = chart.series_id_to_index[series_id];
                chart.series_data[i].push.apply(chart.series_data[i], series_update.data);
              });
            } else {
              // Updates series_data from data
              $.each(data, function(key, datapoint) {
                var timestamp = new Date(datapoint.ts).getTime();
                if (chart.series_callbacks) {
                  // If series_callbacks are provided, call them per series
                  _.each( chart.series_callbacks, function(series_callback, i) {
                    series_callback(timestamp, datapoint.data, i, chart );
                  });
                } else {
                  // By default, pass through values to series in order of metrics list
                  _.each(chart.metrics, function(metric, i) {
                    chart.series_data[i].push([timestamp, datapoint.data[metric]]);
                  });
                }
              });
            }

            // Cull any data older than the window
            var data_until = null;
            _.each(
              chart.series_data,
              function(series_data) {
                if (series_data.length > 0) {
                  var latest_ts = series_data[series_data.length - 1][0];
                  if (data_until == null || data_until < latest_ts) {
                    data_until = latest_ts;
                  }
                  var newest_trash = null;
                  for (var i = 0; i < series_data.length - 1; i++) {
                    if (series_data[i][0] < (latest_ts - config.default_time_boundary)) {
                      newest_trash = i;
                    } else {
                      break;
                    }
                  }
                  if (newest_trash != null) {
                    series_data.splice(0, newest_trash + 1)
                  }
                }
              }
            );

            // shift the floating end
            if (data_until) {
              chart.series_end = new Date(data_until);
              log("Updated series end " + chart.series_end);
            } else {
              log("No data");
            }

            // Update highcharts from series_data
            _.each(
              chart.instance.series,
              function(series,i) {
                series.setData(chart.series_data[i], false)
              }
            );
          }

          chart.instance.redraw();
        },
        error_callback = null,
        blocking = false
      );
    }

    var init = function() {
        render_charts();
        if(config.interval_seconds > 0 ) {
            config.interval_id = setInterval(render_charts, config.interval_seconds * 1000 );
        }
    };

    // Interval based refreshing
    var clear_recurring = function() {
        if( _.isNumber(config.interval_id) ) {
            clearInterval(config.interval_id);    
        }
        config.interval_id = null;
        config.interval_seconds = 0;
    };
    var set_recurring = function (seconds) {
        if ( ! _.isNumber(seconds) ) {
            log("set_recurring(seconds) must be a number");
            return;
        }
        if( ! _.isNull(config.interval_id) ) {
            clearInterval(config.interval_id);
        }
        config.interval_id = setInterval(render_charts,seconds * 1000);
        config.interval_seconds = seconds;
    };

    var destroy = function() {
      clear_recurring();
      _.each(config.charts, function(charts_in_group,chart_group) {
        _.each(charts_in_group, function(chart,chart_key) {
          if(_.isObject(chart.instance)) {
            chart.instance.destroy();
            chart.instance = null;
          }
        });
      });
    }

    // return an object
    return {
        add_chart: add_chart,
        chart_group: chart_group,
        clear_recurring: clear_recurring,
        config: config,
        destroy: destroy,
        init: init,
        render_charts: render_charts,
        set_recurring: set_recurring,
        log: log
    };
}
