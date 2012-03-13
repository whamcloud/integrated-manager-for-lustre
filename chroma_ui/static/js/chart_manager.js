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
	} else { //Stings/Chars/Numbers etc.
		dumped_text = "===>"+arr+"<===("+typeof(arr)+")";
	}
	return dumped_text;
}
var ChartModel = function(options) {

    var config = $.extend(true,  {
        api_params              : {},   // the static params sent to the api request (excluding metrics)
        chart_config            : {},   // highcharts config
        chart_group             : '',   // the chart group. Analagous to the tab
        enabled                 : true, // you can disable a graph by setting this to false
        error_callback          : null, // a callback executed on an error conditoin (not needed really, but an option)
//        get_data                : null, 
        instance                : null, // stores the highcharts instance
        is_zoom                 : false, // whether we have a zoomed graph
        metrics                 : [],    // list of metrics to get
        prep_params             : null,  // callback for custom dynamic paramaters to send to the api
        replace_data_on_update  : false, // if false, appends, if true, resets
        series_begin            : null,  // Date object representing beginning of series
        series_end              : null,  // date object representing end of series
        series_shifting_end     : null,  // floating end date object used for the update
        series_data             : [],    // stores all series data here and updates to here
        series_callbacks        : [],    // list of callbacks for each series
        status                  : 'none', // pending, success, failure
        success_callback        : null,  // optional callback on successful call
        url                     : ''     // url of the metric api to get
    }, options || {});

    if( config.is_zoom ) {
        $.extend(true,config.api_params, {
            xAxis: { labels: { style: { fontSize: '12px'} } },
            yaxis: { labels: { style: { fontSize: '12px', fontWeight: 'bold' } } },
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
        _.each(config.series_callbacks, function() { config.series_data.push([]); } );
    };

    config.reset_series();        
    return config;

};

var ChartManager = function(options) {
	var config = $.extend(true, {
        charts: {},
        chart_group: '',
        debug: true,
        default_time_boundry: 60 * 60 * 1000,
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
        chart_model = ChartModel(options || {});
        config.charts[chart_group][chart_name] = ChartModel(options || {});
    };

    var zoom_options = function() {

    };

    var render_charts = function() {
        log('render_charts');
        _.each(config.charts[config.chart_group], function(chart,key) {
            if (chart.enabled) {
                log('- rendering chart ' + key);
                get_data(chart);
            }
        });
    };

    var default_params = function(api_params,chart) {

        var params = { metrics: chart.metrics.join(",") };
        if ( _.isNull( chart.series_begin) ) {
            chart.series_end          = new Date();
            chart.series_begin        = new Date( chart.series_end - config.default_time_boundry );
        }
        else {
            params.update = 'true';
            chart.series_shifting_end = new Date();
        }
        params.begin = chart.series_begin.toISOString();
        params.end   = chart.series_end.toISOString()

        return $.extend(true, api_params, params );
    };

    var get_data = function(chart) {
        var api_params = $.extend(true, {}, chart.api_params);
        api_params = default_params(api_params, chart);
        // custom params
        if ( _.isFunction(chart.prepare_params) ) {
            api_params = chart.prepare_params(api_params, chart);
        }
        chart.status = 'pending';
        if ( _.isObject(chart.instance) ) {
            chart.instance.showLoading();
        }
        Api.get(
            chart.url,
            api_params,
            success_callback = function(data) {
                chart.status = 'success';
                if ( _.isObject(chart.instance) )
                    chart.instance.hideLoading();
                if ( _.isFunction(chart.success_callback) )
                    chart.success_callback(chart,data);
                
                // do the series callbacks
                //log(dump(data));
                $.each(data, function(key, datapoint) {
                    //log(dump(datapoint));
                    //log(dump(i));
                    var timestamp = new Date(datapoint.ts).getTime();
                    //log(dump(timestamp));
                    _.each( chart.series_callbacks, function(series_callback, i) {
                        series_callback(timestamp, datapoint.data, i, chart );
                    });

                    // init chart
                    if ( _.isNull(chart.instance) ) {
                        chart.instance = new Highcharts.Chart(
                            $.extend(true, {}, chart.chart_config, {
                                // maps all the series data into single object literals with "data" as it's key
                                // this is to allow us to merge it into the config seamlessly
                                series: _.map(
                                            chart.series_data,
                                            function(series_data, i) { return { data: series_data }; }
                                        )
                            })
                        );
                    }
                    // update chart
                    else {
                        // if this is a resource graph we're going to replace the data set, not append to it
                        if (chart.replace_data_on_update )
                            chart.reset_series();

                        _.each(
                            chart.instance.series,
                            function(series,i) { series.setData(chart.series_data[i], false)}
                        );
                        chart.instance.redraw();
                        // shift the floating end
                        // we only update this on the success to allow for failed calls
                        if ( ! _.isNull(chart.series_shifting_end)) {
                            chart.series_end = new Date( chart.series_shifting_end );
                        }
                        //log("END: " + chart.series_end.toISOString());
                    }
                    
                });
            },
            error_callback = function(responseText) {
                chart.status = 'failure';
                if (_.isFunction(chart.error_callback)) {
                    chart.error_callback(responseText);    
                }
            },
            blocking = false
        );
    }

    var init = function() {
        render_charts();
        if(config.interval_seconds > 0 ) {
            config.interval_id = setInterval(render_charts, config.interval_seconds * 1000 );
        }
        return;
    };

    // Interval based refreshing
    var clear_recurring = function() {
        if( _.isNumber(config.interval_id) ) {
            clearInterval(config.interval_id);    
        }
        config.interval_id = null;
        config.interval_seconds = 0;
        return;
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
        return;
    }

    // return an object
    return {
        add_chart: add_chart,
        chart_group: chart_group,
        clear_recurring: clear_recurring,
        config: config,
        init: init,
        render_charts: render_charts,
        set_recurring: set_recurring,
        log: log
    };
}

function chart_manager_dashboard() {
    var chart_manager = ChartManager({chart_group: 'dashboard'});
    chart_manager.add_chart('db_line_cpu_mem', 'dashboard', {
        //url: 'get_fs_stats_for_server/',
        url: 'host/metric',
        api_params: { reduce_fn: 'average' },
        metrics: ["cpu_total", "cpu_user", "cpu_system", "cpu_iowait", "mem_MemFree", "mem_MemTotal"],
        series_callbacks: [
            function(timestamp, data, index, chart) {
                var sum_cpu = data.cpu_user + data.cpu_system + data.cpu_iowait;
                var pct_cpu = (100 * sum_cpu) / data.cpu_total;
                chart.series_data[index].push( [ timestamp, pct_cpu] );
            },
            function( timestamp, data, index, chart ) {
                var used_mem = data.mem_MemTotal - data.mem_MemFree;
                var pct_mem  = 100 * ( used_mem / data.mem_MemTotal );
                chart.series_data[index].push( [ timestamp, pct_mem ]);
            }
        ],
        chart_config: {
            chart: {
                renderTo: 'avgCPUDiv',
                zoomType: 'xy',
                backgroundColor: '#f9f9ff'
            },
            title: { text: 'Server CPU and Memory', style: { fontSize: '12px' } },
            xAxis: { type:'datetime' },
            yAxis: [
                {
                    title: { text: 'Percent Used' },
                    max:100, min:0, startOnTick:false,  tickInterval: 20
                },
            ],
            legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0},
            credits: { enabled:false },
            plotOptions: {
                series:{marker: {enabled: false}},
                column:{ pointPadding: 0.0, shadow: false, groupPadding: 0.0, borderWidth: 0.0 }
            },
            series: [
                { type: 'line', data: [], name: 'cpu' },
                { type: 'line', data: [], name: 'mem' }
            ]
        }
    });
    /*
    chart_manager.add_chart('db_bar_space_usage',{
        url: 'get_fs_stats_for_targets/',
        http_method: 'post',
        metrics: [ "kbytestotal","kbytesfree","filestotal","filesfree" ],
        api_params: {
            targetkind: "OST",
            datafunction: "Average",
            starttime: "",
            filesystem_id: "",
            endtime: ""
        },
        prepare_params: function( params, chart ) {
            return $.extend(true, params, {
                fetchmetrics: chart.metrics.join(" ")
            });
        },
        success_callback: function(chart,data) {
            response = data;
            var free = 0,
                used = 0;
            var freeData = [],
                usedData = [],
                categories = [],
                freeFilesData = [],
                totalFilesData = [];
            var response = data;
            var totalDiskSpace = 0,
                totalFreeSpace = 0,
                totalFiles = 0,
                totalFreeFiles = 0;
            $.each(response, function(resKey, resValue) {
                free = 0, used = 0;
                if (resValue.filesystem != undefined) {
                    totalFreeSpace = resValue.kbytesfree / 1024;
                    totalDiskSpace = resValue.kbytestotal / 1024;
                    free = ((totalFreeSpace / 1024) / (totalDiskSpace / 1024)) * 100;
                    used = 100 - free;

                    freeData.push(free);
                    usedData.push(used);

                    totalFiles = resValue.filesfree / 1024;
                    totalFreeFiles = resValue.filestotal / 1024;
                    free = ((totalFiles / 1024) / (totalFreeFiles / 1024)) * 100;
                    used = 100 - free;

                    freeFilesData.push(free);
                    totalFilesData.push(used);

                    categories.push(resValue.filesystem);
                }
            });

            var series = [
                { data: freeData, stack: 0, name: 'Free Space' },
                { data: usedData, stack: 0, name: 'Used Space' },
                { data: freeFilesData, stack: 1, name: 'Free Files' },
                { data: totalFilesData, stack: 1, name: 'Used Files' }
            ];
            if ( _.isNull(chart.instance) ) {
                var chart_config = $.extend(true, {}, chart.chart_config, {
                    xAxis: { categories: categories },
                    title: { text: "All File System Space Usage" },
                    series: series
                });
                if (chart.is_zoom) {
                    chart_config.chart.renderTo = 'zoomDialog';
                }
                chart.instance = new Highcharts.Chart(chart_config);
                return;
            }
            _.each(series, function(series_object, index) {
                chart.instance.series[index].setData(series_object.data, false);
            });
            chart.instance.redraw();
        },
        chart_config: {
            chart: {
                renderTo: 'container',
                defaultSeriesType: 'column',
                backgroundColor: '#f9f9ff'
            },
            colors: ['#A6C56D', '#C76560', '#A6C56D', '#C76560', '#3D96AE', '#DB843D', '#92A8CD', '#A47D7C', '#B5CA92'],
            plotOptions: { column: { stacking: 'normal' } },
            legend: {
                enabled: false,
                layout: 'vertical',
                align: 'right',
                verticalAlign: 'top',
                x: 0,
                y: 10,
                borderWidth: 0
            },
            title: {
                text: '',
                style: { fontSize: '12px' }
            },
            zoomType: 'xy',
            xAxis: {
                categories: ['Usage'],
                text: '',
                labels: {
                    align: 'right',
                    rotation: 310,
                    style: { fontSize: '8px', fontWeight: 'regular' }
                }
            },
            yAxis: {
                max: 100,
                min: 0,
                startOnTick: false,
                title: { text: 'Percentage' },
                plotLines: [{ value: 0, width: 1, color: '#808080' }]
            },
            credits: { enabled: false },
            tooltip: {
                formatter: function() {
                    var tooltiptext;
                    if (this.point.name) {
                        tooltiptext = '' + this.point.name + ': ' + this.y + '';
                    } else {
                        tooltiptext = '' + this.x + ': ' + this.y;
                    }
                    return tooltiptext;
                }
            },
            labels: {
                items: [{ html: '', style: { left: '40px', top: '8px', color: 'black' } }]
            },
            series: []
        }

    });
    */
    //chart_manager.render_charts();
    chart_manager.init();
    return chart_manager;
};
