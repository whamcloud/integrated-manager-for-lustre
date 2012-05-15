//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

// JSLint option info: http://www.jslint.com/lint.html
/*jslint indent: 2, newcap: true, nomen:true, sloppy: true, undef: true, vars: true, white: true */
/*global _,$ */


var Dashboard = (function() {
  var initialized = false;
  var chart_manager = null;

  var dashboard_type;
  var dashboard_server;
  var dashboard_target;
  var dashboard_filesystem;

  var polling_enabled = true;
  var time_period;

  function stopCharts() {
    // FIXME: revise when there is a global chart_manager
    if (chart_manager) {
      chart_manager.destroy();
    }
  }

  function init() {

    var intervals = {
      minutes: { max: 60, default: 5, factor:   60          },
      hour:    { max: 24, default: 1, factor: 3600          },
      day:     { max: 32, default: 1, factor: 3600 * 24     },
      week:    { max:  4, default: 1, factor: 3600 * 24 * 7 }
    };

    // populate the unit value on changing of the interval_type
    function updateUnits(interval_type, unit_value) {
      var interval = intervals[interval_type];

      // set to "reasonable" default value for interval if exceeds max
      if (unit_value > interval.max) {
        unit_value = interval.default;
      }

      var unit_select_options = _.map(
        _.range(1, interval.max + 1),
        function(i) { return "<option value='"+i+"'>"+i+"</option>"; }
      ).join('');

      $("#unitSelect").html(unit_select_options).val(unit_value);

    }

    // update the available units + trigger change
    $("#intervalSelect").change(function() {
      updateUnits( $(this).val(), $("#unitSelect").val() );
      $("#unitSelect").change();
    });

    // re-init the charts on changing the unit/interval
    $("#unitSelect").change(function(){
      var interval_type = $('#intervalSelect').val();
      var unit_value = $(this).val();

      time_period = intervals[interval_type].factor * unit_value;
      init_charts(chart_manager.config.chart_group);
    });

    // Set defaults
    polling_enabled = true;
    time_period = 5 * 60;
    $('#intervalSelect').val('minutes');
    updateUnits('minutes',5);
    $('input#polling').attr('checked', 'checked');

    $("input#polling").click(function()
    {
      if($(this).is(":checked")) {
        polling_enabled = true;
        chart_manager.set_recurring(10);
        chart_manager.render_charts()
      } else {
        chart_manager.clear_recurring();
        polling_enabled = false;
      }
    });

    $('#zoomDialog').dialog({
      autoOpen: false,
      width: 800,
      height:490,
      show: "clip",
      modal: true,
      position:"center",
      buttons:
      {
        "Close": function() {
          $(this).dialog("close");
        }
      }
    });

    $("#breadcrumb_target").live('change', function ()
    {
      var target_id = $(this).val();
      if(target_id) {
        if (dashboard_filesystem) {
          Backbone.history.navigate("/dashboard/filesystem/" + dashboard_filesystem.id + "/target/" + target_id + "/", {trigger: true});
        } else {
          Backbone.history.navigate("/dashboard/server/" + dashboard_server.id + "/target/" + target_id + "/", {trigger: true});
        }
      }
    });

    $("#breadcrumb_server").live('change', function ()
    {
      var host_id = $(this).val();
      if(host_id) {
        Backbone.history.navigate("/dashboard/server/" + host_id + "/", {trigger: true});
      }
    });

    $("#breadcrumb_filesystem").live('change', function ()
    {
      var filesystem_id = $(this).val();
      if(filesystem_id) {
        Backbone.history.navigate("/dashboard/filesystem/" + filesystem_id + "/", {trigger: true});
      }
    });

    $("#breadcrumb_type").live('change', function ()
    {
      Backbone.history.navigate("/dashboard/" +  $(this).val() + "/", {trigger: true});
    });

    initialized = true;
  }

  function get_view_selection_markup()
  {
    var view_selection_markup = "<select id='breadcrumb_type'>";
    if(dashboard_type === "filesystem") {
      view_selection_markup += "<option value='filesystem' selected>File systems</option>";
    }
    else {
      view_selection_markup += "<option value='filesystem'>File systems</option>";
    }

    if(dashboard_type === "server") {
      view_selection_markup += "<option value='server' selected>Servers</option>";
    }
    else {
      view_selection_markup += "<option value='server'>Servers</option>";
    }

    view_selection_markup += "</select>";
    return view_selection_markup;
  }

  function setPath(type, id_1, id_2) {
    /*
     :param type: 'server' or 'filesystem'
     :param id_1: Server ID if type=='server', else Filesystem ID (may be undefined)
     :param id_2: Target ID (may be undefined)
     */
    if (!initialized) {
      init();
    }

    dashboard_type = type;
    dashboard_server = undefined;
    dashboard_target = undefined;
    dashboard_filesystem = undefined;

    if (id_1) {
      if (type === 'server') {
        dashboard_server = ApiCache.get('host', id_1).toJSON();
        if (id_2) {
          // Showing a target within a server
          dashboard_target = ApiCache.get('target', id_2).toJSON();
          load_target_page();
        } else {
          // Showing a server
          load_server_page();
        }
      } else if (type === 'filesystem') {
        dashboard_filesystem = ApiCache.get('filesystem', id_1).toJSON();
        if (id_2) {
          dashboard_target = ApiCache.get('target', id_2).toJSON();
          // Showing a target within a filesystem
          load_target_page();
        } else {
          // Showing a filesystem
          load_filesystem_page();
        }
      }
    } else {
      // Top level view
      load_global_page();
    }
  }

  function dashboard_page(page) {
    $('.dashboard_page').hide();
    $('#dashboard_page_' + page).show();
    updateChartSizes();
  }

  function load_server_page()
  {
    dashboard_page('server');

    var ostKindMarkUp = "<option value=''></option>";
    var ost_file_system_MarkUp = "<option value=''></option>";

    var breadCrumbHtml = "<ul>"+
      "<li><a href='dashboard/' class='home_icon navigation'>Home</a></li>"+
      "<li>"+get_view_selection_markup()+"</li>";
    breadCrumbHtml += "<li><select id='breadcrumb_server'></select></li>";

    breadCrumbHtml += "<li>"+
      "<select id='breadcrumb_target'>"+
      "<option value=''>Select Target</option>";

    Api.get("target/", {"host_id": dashboard_server.id, limit: 0},
      success_callback = function(data)
      {
        var targets = data.objects;
        targets = targets.sort(function(a,b) {return a.label > b.label;});

        var count = 0;
        $.each(targets, function(i, target_info)
        {
          breadCrumbHtml += "<option value='" + target_info.id + "'>" + target_info.label + "</option>";
          ostKindMarkUp = ostKindMarkUp + "<option value="+target_info.id+">"+target_info.kind+"</option>";
          ost_file_system_MarkUp = ost_file_system_MarkUp + "<option value="+target_info.id+">"+target_info.filesystem_id+"</option>";
          count += 1;
        });

        breadCrumbHtml = breadCrumbHtml +
          "</select>"+
          "</li>"+
          "</ul>";
        $("#breadcrumbs").html(breadCrumbHtml);
        populate_breadcrumb_server(ApiCache.list('host'));

        $('#ossSummaryTblDiv').show();
        $('#serverSummaryTblDiv').show();
      });

    init_charts('servers');
  }

  function load_target_page()
  {
    dashboard_page('target');

    var breadCrumbHtml = "<ul>"+
      "<li><a href='dashboard/' class='home_icon navigation'>Home</a></li>"+
      "<li>"+get_view_selection_markup()+"</li>";
    if (dashboard_filesystem){
      breadCrumbHtml += "<li><a class='navigation' href='dashboard/filesystem/" + dashboard_filesystem.id + "/''>"+dashboard_filesystem.label+"</a></li>";
    } else {
      breadCrumbHtml += "<li><a class='navigation' href='dashboard/server/" + dashboard_server.id + "/'>"+dashboard_server.label+"</a></li>";
    }

    $('#target_name').html(dashboard_target.label);

    breadCrumbHtml += "<li>"+dashboard_target.label+"</li>"+
      "</ul>";

    $("#breadcrumbs").html(breadCrumbHtml);

    if (dashboard_target.filesystem) {
      var innerContent = "";
      $('#ostSummaryTbl').html("<tr><td width='100%' align='center' height='180px'>" +
        "<img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' /></td></tr>");

      var filesystem = ApiCache.get('filesystem', dashboard_target.filesystem_id).toJSON();
      innerContent = innerContent +
        "<tr>" +
        "<td class='greybgcol'>MGS :</td><td class='tblContent greybgcol'>"+filesystem.mgt.primary_server_name+"</td><td>&nbsp;</td><td>&nbsp;</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>MDS :</td>" +
        "<td class='tblContent greybgcol'>"+filesystem.mdts[0].primary_server_name+"</td>" +
        "<td></td><td></td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>File System :</td>" +
        "<td class='tblContent greybgcol'>"+filesystem.name+"</td>" +
        "<td>&nbsp;</td>" +
        "<td>&nbsp;</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Size: </td>" +
        "<td class='tblContent greybgcol'>"+formatBytes(filesystem.bytes_total)+" </td>" +
        "<td class='greybgcol'>Free space:</td>" +
        "<td class='tblContent greybgcol'>"+formatBytes(filesystem.bytes_free)+"</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Max. files: </td>" +
        "<td class='tblContent greybgcol'>"+formatBigNumber(filesystem.files_total)+" </td>" +
        "<td class='greybgcol'>Files:</td>" +
        "<td class='tblContent greybgcol'>"+formatBigNumber(filesystem.files_total - filesystem.files_free)+"</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Total OSTs:</td>" +
        "<td class='tblContent greybgcol'>"+filesystem.osts.length+" </td>" +
        "<td>&nbsp;</td><td>&nbsp;</td>" +
        "</tr>";

      $('#ostSummaryTbl').html(innerContent);
    }
    else
    {
      $('#ostSummaryTbl').html("");
    }

    if(dashboard_target.kind === 'OST') {
      //ost_Pie_Space_Data($('#ls_ostId').val(), $('#ls_ostName').val(), "", "", "Average", $('#ls_ostKind').val(), spaceUsageFetchMatric, "false");
      //ost_Pie_Inode_Data($('#ls_ostId').val(), $('#ls_ostName').val(), "", "", "Average", $('#ls_ostKind').val(), spaceUsageFetchMatric, "false");
      //ost_Area_ReadWrite_Data($('#ls_ostId').val(), $('#ls_ostName').val(), startTime, endTime, "Average", $('#ls_ostKind').val(), readWriteFetchMatric, "false");
      $("#target_space_usage_container,#target_inodes_container,#target_read_write_container_div").show();
      $("#target_mdt_ops_container_div").hide();
      init_charts('targets_ost');

    }
    else if (dashboard_target.kind === 'MDT') {
      //ost_Area_mgtOps_Data($('#ls_ostId').val(), "false");
      $("#target_space_usage_container,#target_read_write_container_div").hide();
      $("td.target_space_usage div.magni").hide();
      $("#target_mdt_ops_container_div,#target_inodes_container").show();
      init_charts('targets_mdt');
    }
    else {
      $("#target_space_usage_container,#target_inodes_container,#target_read_write_container_div,#target_mdt_ops_container_div").hide();
      $("td.target_space_usage div.magni").hide();
      $("td.target_inodes div.magni").hide();
    }
  }

  function load_filesystem_page()
  {
    dashboard_page('filesystem');

    var ostKindMarkUp = "<option value=''></option>";

    var breadCrumbHtml = "<ul>"+
      "<li><a href='dashboard/' class='home_icon navigation'>Home</a></li>" +
      "<li>"+get_view_selection_markup()+"</li>" +
      "<li><select id='breadcrumb_filesystem'></select></li>" +
      "<li>"+
      "<select id='breadcrumb_target'>" + "<option value=''>Select Target</option>";


    Api.get("target/", {"filesystem_id": dashboard_filesystem.id, limit: 0},
      success_callback = function(data)
      {
        var targets = data.objects;
        targets = targets.sort(function(a,b) {return a.label > b.label;});

        var count = 0;
        $.each(targets, function(i, target_info)
        {
          breadCrumbHtml += "<option value='" + target_info.id + "'>" + target_info.label + "</option>";

          ostKindMarkUp = ostKindMarkUp + "<option value="+target_info.id+">"+target_info.kind+"</option>";

          count += 1;
        });

        breadCrumbHtml = breadCrumbHtml +
          "</select>"+
          "</li>"+
          "</ul>";
        $("#breadcrumbs").html(breadCrumbHtml);
        populate_breadcrumb_filesystem(ApiCache.list('filesystem'));

        $("#ostKind").html(ostKindMarkUp);
      });

    init_charts('filesystem');

    $('#filesystem_name').html(dashboard_filesystem.label);
    var innerContent = "";
    innerContent = innerContent +
      "<tr>" +
      "<td>MGS :</td>" +
      "<td>"+dashboard_filesystem.mgt.primary_server_name+"</td>" +
      "</tr>"+
      "<tr>" +
      "<td>MDS:</td>" +
      "<td>"+dashboard_filesystem.mdts[0].primary_server_name+"</td>" +
      "</tr>"+
      "<tr>" +
      "<td>Total OSTs:</td>" +
      "<td>"+dashboard_filesystem.osts.length+"</td>" +
      "</tr>"+
      "<tr>" +
      "<td>Capacity used: </td>" +
      "<td>"+formatBytes(dashboard_filesystem.bytes_total - dashboard_filesystem.bytes_free)+"/" + formatBytes(dashboard_filesystem.bytes_total) + "</td>" +
      "</tr>"+
      "<tr>" +
      "<td>Files used: </td>" +
      "<td>"+formatBigNumber(dashboard_filesystem.files_total - dashboard_filesystem.files_free)+"/" + formatBigNumber(dashboard_filesystem.files_total) + "</td>" +
      "</tr>";

    $('#fileSystemSummaryTbl').html(innerContent);
  }


  function load_global_page()
  {
    dashboard_page('global');

    var filesystem_rows = "";
    _.each(ApiCache.list('filesystem'), function(filesystem) {
      var t = _.template("<tr><td class='icon_columns'><%= LiveObject.alertIcon(filesystem) %></td><td><%= filesystem.name %></td><td align='right'><%= formatBytes(filesystem.bytes_total) %></td><td align='right'><%= formatBytes(filesystem.bytes_free) %></td></tr>");
      filesystem_rows += t({filesystem: filesystem});
    });
    $('#global_filesystem_table').find('tbody').html(filesystem_rows);


    var breadCrumbHtml = "<ul>" +
    "  <li><a href='dashboard/' class='home_icon navigation'>Home</a></li>" +
    "  <li>" + get_view_selection_markup() + "</li>" +
    "  </li>" +
    "  <li>" +
    "    <select id='breadcrumb_filesystem'>" +
    "    </select>" +
    "    <select id='breadcrumb_server'>" +
    "    </select>" +
    "  </li>" +
    "</ul>";

    $('#breadcrumbs').html(breadCrumbHtml);
    if (dashboard_type === 'filesystem') {
      $('#breadcrumb_server').hide();
      populate_breadcrumb_filesystem(ApiCache.list('filesystem'));
    } else if (dashboard_type === 'server') {
      $('#breadcrumb_filesystem').hide();
      populate_breadcrumb_server(ApiCache.list('host'));
    }
    $(this).find('option:selected').val();
    init_charts('dashboard');
  }

  function bytes_rate_formatter() {
    return bytes_formatter.apply(this) + "/s";
  }

  function bytes_formatter() {
    if (this.value < 0) {
      this.value = this.value * -1;
    }
    /*jslint eqeq: true */
    if (this.value == 0) {
      // No units on zeros, it's meaningless.
      return this.value;
    }
    /*jslint eqeq: false */

    var l = "" + formatBytes(this.value, 2);
    if (l[0] === '-') {
      return l.substr(1);
    }
    return l;
  }

  function percentage_formatter() {
    return this.value + "%";
  }

  /*jslint eqeq: true */
  function whole_numbers_only_formatter() {
    if (Math.round(this.value) != this.value){
      return "";
    }
    return this.value;
  }
  /*jslint eqeq: false */

  function init_charts(chart_group) {
    /* helper callbacks */
    var api_params_add_filessytem = function(api_params,chart) {
      api_params.filesystem_id = dashboard_filesystem.id;
      return api_params;
    };

    if (!_.isNull(chart_manager)) {
      chart_manager.destroy();
    }

    chart_manager = ChartManager({chart_group: 'dashboard', default_time_boundary: time_period * 1000});
    chart_manager.add_chart('db_line_cpu_mem', 'dashboard', {
      url: 'host/metric/',
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
          renderTo: 'global_cpu_mem'
        },
        title: { text: 'CPU/RAM Usage'},
        xAxis: { type:'datetime' },
        legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0},
        yAxis: [{
          max:100, min:0, startOnTick:false,  tickInterval: 20,
          title: null,
          labels: {formatter: percentage_formatter}
        }],
        series: [
          { type: 'line', data: [], name: 'cpu' },
          { type: 'line', data: [], name: 'ram' }
        ]
      }
    });

    chart_manager.add_chart('iops', 'dashboard', {
      url: 'target/metric/',
      api_params: {kind: 'OST'},
      metrics: ["stats_write_bytes", "stats_read_bytes"],
      data_callback: function(chart, data) {
        // Generate a number of series objects and return them
        var result = {};
        _.each(data, function(series_data, target_id) {
          var update_data = [];
          _.each(series_data, function(datapoint) {
              var timestamp = new Date(datapoint.ts).getTime();
              var read_bytes = _.isUndefined(datapoint.data.stats_read_bytes)? 0 : datapoint.data.stats_read_bytes;
              var write_bytes =  _.isUndefined(datapoint.data.stats_write_bytes)? 0 : datapoint.data.stats_write_bytes;
              update_data.push([timestamp, read_bytes - write_bytes]);
            });

          var target = ApiCache.get('target', target_id);
          var label;
          if (target) {
            label = target.attributes.label;
            result[target_id] = {
              id: target_id,
              label: label,
              data: update_data
            };
          } else {
            // Exclude the target from the result this time, next time around
            // the ApiCache will have caught up and we'll give some data
            // with a proper axis name
          }

        });

        return result;
      },
      series_template: {type: 'areaspline'},
      chart_config: {
        chart: {
          renderTo: 'global_ost_bandwidth'
        },
        title: { text: 'OST Read/Write balance'},
        xAxis: {type:'datetime'},
        yAxis: [{
          title: null,
          labels: {formatter: bytes_rate_formatter}
        }],
        plotOptions: {
          areaspline: {
            stacking: 'normal'
          }
        },
        legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0}
      }
    });

    chart_manager.add_chart('mdops', 'dashboard', {
      url: 'target/metric/',
      api_params: { reduce_fn: 'sum', kind: 'MDT'},
      metrics: ["stats_close", "stats_getattr", "stats_getxattr", "stats_link",
        "stats_mkdir", "stats_mknod", "stats_open", "stats_rename",
        "stats_rmdir", "stats_setattr", "stats_statfs", "stats_unlink"],
      chart_config: {
        chart: {
          renderTo: 'global_metadata_ops'
        },
        title: { text: 'Metadata Operations'},
        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'ops/s' }}],
        colors: [
          '#63B7CF',
          '#9277AF',
          '#A6C56D',
          '#C76560',
          '#6087B9',
          '#DB843D',
          '#92A8CD',
          '#A47D7C',
          '#B5CA92'
        ],
        series: [
          {name: 'close', type: 'area'},
          {name: 'getattr', type: 'area'},
          {name: 'getxattr', type: 'area'},
          {name: 'link', type: 'area'},
          {name: 'mkdir', type: 'area'},
          {name: 'mknod', type: 'area'},
          {name: 'open', type: 'area'},
          {name: 'rename', type: 'area'},
          {name: 'rmdir', type: 'area'},
          {name: 'setattr', type: 'area'},
          {name: 'statfs', type: 'area'},
          {name: 'unlink', type: 'area'}
        ]
      }
    });

    chart_manager.add_chart('readwrite', 'dashboard', {
      url: 'target/metric/',
      api_params: { reduce_fn: 'sum', kind: 'OST'},
      metrics: ["stats_read_bytes", "stats_write_bytes"],
      series_callbacks: [
        function(timestamp, data, index, chart) {
          chart.series_data[index].push( [ timestamp, data.stats_read_bytes] );
        },
        function( timestamp, data, index, chart ) {
          chart.series_data[index].push( [ timestamp, -data.stats_write_bytes] );
        }
      ],
      chart_config: {
        chart: {
          renderTo: 'global_read_write'
        },
        title: { text: 'Read/Write bandwidth'},
        xAxis: { type:'datetime' },
        yAxis: [
          {title: null,
           labels: {formatter: bytes_rate_formatter}}],
        series: [
          { type: 'area', name: 'read' },
          { type: 'area', name: 'write' }
        ]
      }
    });

    chart_manager.add_chart('freespace', 'dashboard', {
      url: 'target/metric/',
      api_params: {reduce_fn: 'sum', kind: 'OST', group_by: 'filesystem', latest: true},
      metrics: ["kbytestotal", "kbytesfree", "filestotal", "filesfree"],
      snapshot: true,
      snapshot_callback: function(chart, data) {
        var categories = [];
        var freeBytes = [];
        var usedBytes = [];
        var freeFiles = [];
        var usedFiles = [];

        _.each(data, function(fs_data, fs_id) {
          var name;
          var filesystem = ApiCache.get('filesystem', fs_id);
          if (filesystem) {
            name = filesystem.attributes.name;
          } else {
            name = fs_id;
          }
          categories.push(name);

          if (fs_data.length) {
            var current_data = fs_data[0].data;
            var free;

            free = ((current_data.kbytesfree)/(current_data.kbytestotal))*100;
            freeBytes.push(free);
            usedBytes.push(100 - free);

            free = ((current_data.filesfree)/(current_data.filestotal))*100;
            freeFiles.push(free);
            usedFiles.push(100 - free);
          } else {
            // No data, assume new
            freeBytes.push(100);
            usedBytes.push(0);
            freeFiles.push(100);
            usedFiles.push(0);
          }
        });

        chart.instance.xAxis[0].setCategories(categories);
        chart.instance.series[0].setData(freeBytes, false);
        chart.instance.series[1].setData(usedBytes, false);
        chart.instance.series[2].setData(freeFiles, false);
        chart.instance.series[3].setData(usedFiles, false);
      },
      chart_config: {
        chart: {
          renderTo: 'global_usage'
        },
        title: { text: 'Usage'},
        series: [
          { type: 'column', stack: 0, name: 'Free bytes'},
          { type: 'column', stack: 0, name: 'Used bytes'},
          { type: 'column', stack: 1, name: 'Free files'},
          { type: 'column', stack: 1, name: 'Used files'}
        ],
        plotOptions: {
          column: {
            stacking: 'normal',
            pointWidth: 30.0
          }
        },
        xAxis:{ categories: ['Usage'], text: '', labels : {align: 'right', rotation: 310, style:{fontSize:'8px', fontWeight:'regular'} } },
        yAxis:{
          max:100, min:0, startOnTick:false,
          title:null,
          labels: {formatter: percentage_formatter},
          plotLines: [ { value: 0,width: 1, color: '#808080' } ]
        },
        labels:{ items:[{html: '',style:{left: '40px',top: '8px',color: 'black'}}]},
        colors: [
          '#A6C56D',
          '#C76560',
          '#A6C56D',
          '#C76560'
        ]
      }
    });

    chart_manager.add_chart('client_count', 'dashboard', {
      url: 'target/metric/',
      api_params: { reduce_fn: 'sum', kind: 'MDT'},
      metrics: ["client_count"],
      chart_config: {
        chart: {
          renderTo: 'global_client_count'
        },
        title: { text: 'Client count'},
        xAxis: { type:'datetime' },
        yAxis: [
          {title: null, labels: {formatter: whole_numbers_only_formatter}}],
        series: [
          { type: 'line', data: [], name: 'Client count' }
        ]
      }
    });

    // oss
    chart_manager.chart_group('servers');
    chart_manager.add_chart('cpu','servers', {
      url: function() { return 'host/' + dashboard_server.id + '/metric/'; },
      api_params: { reduce_fn: 'average' },
      metrics: ["cpu_total", "cpu_user", "cpu_system", "cpu_iowait"],
      series_callbacks: [
        function(timestamp, data, index, chart) {
          var pct_user = ((100 * data.cpu_user + (data.cpu_total / 2)) / data.cpu_total);
          chart.series_data[index].push( [ timestamp, pct_user] );
        },
        function(timestamp, data, index, chart) {
          var pct_system = ((100 * data.cpu_system + (data.cpu_total / 2)) / data.cpu_total);
          chart.series_data[index].push( [ timestamp, pct_system] );
        },
        function(timestamp, data, index, chart) {
          var pct_iowait = ((100 * data.cpu_iowait + (data.cpu_total / 2)) / data.cpu_total);
          chart.series_data[index].push( [ timestamp, pct_iowait] );
        }
      ],
      chart_config: {
        chart: { renderTo: 'server_cpu'},
        title: { text: 'CPU usage'},
        xAxis: { type:'datetime' },
        legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0},
        yAxis: [{
          title: null,
          labels: {formatter: percentage_formatter},
          max:100, min:0, startOnTick:false,  tickInterval: 20
        }],
        series: _.map(
          [ 'user','system','iowait'],
          function(metric) { return { type: 'line', data: [], name: metric }; }
        )
      }
    });

    chart_manager.chart_group('servers');
    chart_manager.add_chart('mem','servers', {
      url: function() { return 'host/' + dashboard_server.id + '/metric/'; },
      api_params: { reduce_fn: 'average' },
      metrics: ["mem_MemFree", "mem_MemTotal", 'mem_SwapTotal', 'mem_SwapFree'],

      series_callbacks: [
        function( timestamp, data, index, chart ) {
          chart.series_data[index].push( [ timestamp, data.mem_MemTotal*1024 ]);
        },
        function( timestamp, data, index, chart ) {
          chart.series_data[index].push( [ timestamp, data.mem_MemTotal*1024 - data.mem_MemFree*1024]);
        },
        function( timestamp, data, index, chart ) {
          chart.series_data[index].push( [ timestamp, data.mem_SwapTotal*1024 ]);
        },
        function( timestamp, data, index, chart ) {
          chart.series_data[index].push( [ timestamp, data.mem_SwapTotal*1024 - data.mem_SwapFree*1024 ]);
        }
      ],
      chart_config: {
        chart: { renderTo: 'server_mem'},
        title: { text: 'Memory usage'},
        xAxis: { type:'datetime'},
        legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0},
        yAxis: [{
          title: null,
          labels: {formatter: bytes_formatter},
          min: 0
        }],
        series: _.map(
          ['Total memory', 'Used memory', 'Total swap', 'Used swap'],
          function(metric) { return { type: 'line', data: [], name: metric }; }
        )
      }
    });

    chart_manager.add_chart('readwrite', 'servers', {
      // FIXME: filter by targets on this server
      url: function() { return 'target/metric/'; },
      api_params: { reduce_fn: 'sum', kind: 'OST'},
      metrics: ["stats_read_bytes", "stats_write_bytes"],
      series_callbacks: [
        function(timestamp, data, index, chart) {
          chart.series_data[index].push( [ timestamp, data.stats_read_bytes] );
        },
        function( timestamp, data, index, chart ) {
          chart.series_data[index].push( [ timestamp, -data.stats_write_bytes] );
        }
      ],
      chart_config: {
        chart: { renderTo: 'server_read_write'},
        title: { text: 'Read/Write bandwidth'},
        xAxis: { type:'datetime' },
        yAxis: [{
          title: null,
          labels: {formatter: bytes_rate_formatter}
        }],
        series: [
          { type: 'area', name: 'read' },
          { type: 'area', name: 'write' }
        ]
      }
    });

    // ost
    chart_manager.chart_group('targets_ost');
    chart_manager.add_chart('freespace','targets_ost', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/'; },
      api_params: {reduce_fn: 'sum', kind: 'OST', group_by: 'filesystem', latest: true},
      metrics: ["kbytestotal", "kbytesfree"],
      snapshot: true,
      snapshot_callback: function(chart, data) {
        var free=0,used=0;
        var totalDiskSpace=0,totalFreeSpace=0;
        if ( _.isObject(data[0])) {
          totalFreeSpace = data[0].data.kbytesfree;
          totalDiskSpace = data[0].data.kbytestotal;
          free = Math.round(((totalFreeSpace)/(totalDiskSpace))*100);
          used = Math.round(100 - free);
        }
        chart.instance.series[0].setData([ ['Free', free], ['Used', used] ]);
      },
      chart_config: {
        chart: {
          renderTo: 'target_space_usage_container',
          plotShadow: false
        },
        colors: [ '#A6C56D', '#C76560' ],
        title:{ text: 'Space Usage' },
        zoomType: 'xy',
        tooltip: {
          formatter: function() { return '<b>'+ this.point.name +'</b>: '+ this.percentage +' %'; }
        },
        xAxis:{ categories: [], text: '' },
        yAxis:{ text: '', plotLines: [ { value: 0, width: 1, color: '#808080' } ] },
        plotOptions: {
          pie: {
            allowPointSelect: true,
            cursor: 'pointer',
            showInLegend: true,
            size: '100%',
            dataLabels: { enabled: false,color: '#000000',connectorColor: '#000000' }
          }
        },
        series: [{
          type: 'pie',
          name: 'Browser share',
          data: [ ]
        }]
      }
    });
    chart_manager.add_chart('inode','targets_ost', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/'; },
      api_params: {reduce_fn: 'sum', kind: 'OST', group_by: 'filesystem', latest: true},
      metrics: ["filestotal", "filesfree"],
      snapshot: true,
      snapshot_callback: function(chart, data) {
        var free=0,used=0;
        var totalFiles=0,totalFreeFiles=0;
        if ( _.isObject(data[0])) {
          totalFiles = data[0].data.filesfree;
          totalFreeFiles = data[0].data.filestotal;
          free = Math.round(((totalFiles)/(totalFreeFiles))*100);
          used = Math.round(100 - free);
        }
        chart.instance.series[0].setData([ ['Free', free], ['Used', used] ]);
      },
      chart_config: {
        chart: {
          renderTo: 'target_inodes_container',
          plotShadow: false
        },
        colors: [ '#A6C56D', '#C76560' ],
        title:{ text: 'File usage'},
        zoomType: 'xy',
        tooltip: {
          formatter: function() { return '<b>'+ this.point.name +'</b>: '+ this.percentage +' %'; }
        },
        xAxis:{ categories: [], text: '' },
        yAxis:{ text: '', plotLines: [ { value: 0, width: 1, color: '#808080' } ] },
        plotOptions: {
          pie: {
            allowPointSelect: true,
            cursor: 'pointer',
            showInLegend: true,
            size: '100%',
            dataLabels: { enabled: false,color: '#000000',connectorColor: '#000000' }
          }
        },
        series: [{
          type: 'pie',
          name: 'Browser share',
          data: [ ]
        }]
      }
    });

    chart_manager.add_chart('readwrite', 'targets_ost', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/'; },
      api_params: { reduce_fn: 'sum', kind: 'OST'},
      metrics: ["stats_read_bytes", "stats_write_bytes"],
      series_callbacks: [
        function(timestamp, data, index, chart) {
          chart.series_data[index].push( [ timestamp, data.stats_read_bytes] );
        },
        function( timestamp, data, index, chart ) {
          chart.series_data[index].push( [ timestamp, -data.stats_write_bytes] );
        }
      ],
      chart_config: {
        colors: [ '#6285AE', '#AE3333', '#A6C56D', '#C76560', '#3D96AE', '#DB843D', '#92A8CD',  '#A47D7C',  '#B5CA92' ],
        chart: {
          renderTo: 'target_read_write_container'
        },
        legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
        title: { text: 'Read vs Writes'},
        tooltip: { formatter: function()  { return ''+ this.series.name +': '+ this.y +''; } },

        xAxis: { type:'datetime' },
        yAxis: [{
          title: null,
          labels: {formatter: bytes_rate_formatter}
        }],
        series: [
          { type: 'area', name: 'Read', data: []},
          { type: 'area', name: 'Write',data: []}
        ]
      }
    });

    chart_manager.chart_group('targets_mdt');
    chart_manager.add_chart('mdops', 'targets_mdt', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/'; },
      api_params: {},
      metrics: ["stats_close", "stats_getattr", "stats_getxattr", "stats_link",
        "stats_mkdir", "stats_mknod", "stats_open", "stats_rename",
        "stats_rmdir", "stats_setattr", "stats_statfs", "stats_unlink"],
      chart_config: {
        chart: {
          renderTo: 'target_mdt_ops_container'
        },
        tooltip: { formatter: function() { return ''+ this.x +': '+ Highcharts.numberFormat(this.y, 0, ',') +' '; } },

        title: { text: 'Metadata Operations'},
        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'ops/s' }}],
        colors: [ '#63B7CF', '#9277AF', '#A6C56D', '#C76560', '#6087B9', '#DB843D', '#92A8CD', '#A47D7C',  '#B5CA92' ],
        series: _.map(
          ['close','getattr','getxattr','link','mkdir','mknod','open','rename','rmdir','setattr','statfs','unlink'],
          function(metric, i) { return { name: metric, type: 'area' }; }
        )
      }
    });

    chart_manager.add_chart('inode','targets_mdt', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/'; },
      api_params: { latest: true},
      metrics: ["filestotal", "filesfree"],
      snapshot: true,
      snapshot_callback: function(chart, data) {
        var free=0,used=0;
        var totalFiles=0,totalFreeFiles=0;
        if ( _.isObject(data[0])) {
          totalFiles = data[0].data.filesfree;
          totalFreeFiles = data[0].data.filestotal;
          free = Math.round(((totalFiles)/(totalFreeFiles))*100);
          used = Math.round(100 - free);
        }
        chart.instance.series[0].setData([ ['Free', free], ['Used', used] ]);
      },
      chart_config: {
        chart: {
          renderTo: 'target_inodes_container',
          plotShadow: false
        },
        colors: [ '#A6C56D', '#C76560' ],
        title:{ text: 'File usage'},
        zoomType: 'xy',
        tooltip: {
          formatter: function() { return '<b>'+ this.point.name +'</b>: '+ this.percentage +' %'; }
        },
        xAxis:{ categories: [], text: '' },
        yAxis:{ text: '', plotLines: [ { value: 0, width: 1, color: '#808080' } ] },
        plotOptions: {
          pie: {
            allowPointSelect: true,
            cursor: 'pointer',
            showInLegend: true,
            size: '100%',
            dataLabels: { enabled: false,color: '#000000',connectorColor: '#000000' }
          }
        },
        series: [{
          type: 'pie',
          name: 'Browser share',
          data: [ ]
        }]
      }
    });

    chart_manager.chart_group('filesystem');
    chart_manager.add_chart('freespace','filesystem', {
      url: 'target/metric/',
      api_params: {reduce_fn: 'sum', kind: 'OST', group_by: 'filesystem', latest: true },
      api_params_callback: api_params_add_filessytem,
      metrics: ["kbytestotal", "kbytesfree", "filestotal", "filesfree"],
      snapshot: true,
      snapshot_callback: function(chart, data) {
        var categories = [];
        var freeBytes  = [];
        var usedBytes  = [];
        var freeFiles  = [];
        var usedFiles  = [];

        _.each(data, function(fs_data, fs_id) {
          var name;
          var filesystem = ApiCache.get('filesystem', fs_id);
          if (filesystem) {
            name = filesystem.attributes.name;
          } else {
            name = fs_id;
          }
          categories.push(name);

          if (fs_data.length) {
            var current_data = fs_data[0].data;
            var free;

            free = ((current_data.kbytesfree)/(current_data.kbytestotal))*100;
            freeBytes.push(free);
            usedBytes.push(100 - free);

            free = ((current_data.filesfree)/(current_data.filestotal))*100;
            freeFiles.push(free);
            usedFiles.push(100 - free);
          } else {
            // No data, assume new
            freeBytes.push(100);
            usedBytes.push(0);
            freeFiles.push(100);
            usedFiles.push(0);
          }
        });

        chart.instance.xAxis[0].setCategories(categories);
        chart.instance.series[0].setData(freeBytes, false);
        chart.instance.series[1].setData(usedBytes, false);
        chart.instance.series[2].setData(freeFiles, false);
        chart.instance.series[3].setData(usedFiles, false);
      },
      chart_config: {
        chart: {
          renderTo: 'filesystem_usage'
        },
        title: { text: 'Usage'},
        series: [
          { type: 'column', stack: 0, name: 'Free bytes'},
          { type: 'column', stack: 0, name: 'Used bytes'},
          { type: 'column', stack: 1, name: 'Free files'},
          { type: 'column', stack: 1, name: 'Used files'}
        ],
        plotOptions: {
          column: {
            stacking: 'normal',
            pointWidth: 30.0
          }
        },
        xAxis:{ categories: ['Usage'], text: '', labels : {align: 'right', rotation: 310, style:{fontSize:'8px', fontWeight:'regular'} } },
        yAxis:{max:100, min:0, startOnTick:false,
          title: null,
          labels: {formatter: percentage_formatter},
          plotLines: [ { value: 0,width: 1, color: '#808080' } ] },
        labels:{ items:[{html: '',style:{left: '40px',top: '8px',color: 'black'}}]},
        colors: [
          '#A6C56D',
          '#C76560',
          '#A6C56D',
          '#C76560'
        ]
      }
    });
    chart_manager.add_chart('client_count','filesystem', {
      url: 'target/metric/',
      api_params: { reduce_fn: 'sum', kind: 'MDT'},
      api_params_callback: api_params_add_filessytem,
      metrics: ["client_count"],
      chart_config: {
        chart: {
          renderTo: 'filesystem_client_count'
        },
        title: { text: 'Client count'},
        xAxis: { type:'datetime' },
        yAxis: [{
          title: { text: 'Clients' },
          plotLines: [{ value: 0, width: 1, color: '#808080' }]
        }],
        yAxis: [
          {title: null, labels: {formatter: whole_numbers_only_formatter}}],
        series: [
          { type: 'line', data: [], name: 'Client count' }
        ]
      }
    });
    chart_manager.add_chart('cpumem','filesystem', {
      url: 'host/metric/',
      api_params: { reduce_fn: 'average' },
      api_params_callback: api_params_add_filessytem,
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
          renderTo: 'filesystem_cpu_mem'
        },
        title: { text: 'CPU/RAM Usage'},
        xAxis: { type:'datetime' },
        legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0},
        yAxis: [{
          title: null,
          labels: {formatter: percentage_formatter},
          max:100,
          min:0,
          startOnTick:false,
          tickInterval: 20
        }],
        series: [
          { type: 'line', data: [], name: 'cpu' },
          { type: 'line', data: [], name: 'ram' }
        ]
      }
    });
    chart_manager.add_chart('readwrite','filesystem', {
      url: 'target/metric/',
      api_params: { reduce_fn: 'sum', kind: 'OST'},
      api_params_callback: api_params_add_filessytem,
      metrics: ["stats_read_bytes", "stats_write_bytes"],
      series_callbacks: [
        function(timestamp, data, index, chart) {
          chart.series_data[index].push( [ timestamp, ( data.stats_read_bytes)] );
        },
        function( timestamp, data, index, chart ) {
          chart.series_data[index].push( [ timestamp, - ( data.stats_write_bytes) ] );
        }
      ],
      chart_config: {
        chart: {
          renderTo: 'filesystem_read_write'
        },
        title: { text: 'Read vs Writes'},
        xAxis: { type:'datetime' },
        yAxis: [{
          title: null,
          labels: {formatter: bytes_rate_formatter}
        }],
        tooltip:  { formatter: function()  { return ''+this.series.name +': '+ this.y +''; } },
        series: [
          { type: 'area', name: 'read' },
          { type: 'area', name: 'write' }
        ]
      }
    });
    chart_manager.add_chart('mdops','filesystem', {
      url: 'target/metric/',
      api_params: { reduce_fn: 'sum', kind: 'MDT'},
      api_params_callback: api_params_add_filessytem,
      metrics: ["stats_close", "stats_getattr", "stats_getxattr", "stats_link",
        "stats_mkdir", "stats_mknod", "stats_open", "stats_rename",
        "stats_rmdir", "stats_setattr", "stats_statfs", "stats_unlink"],
      chart_config: {
        chart: {
          renderTo: 'filesystem_md_ops'
        },
        title: { text: 'Metadata op/s'},
        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'MD op/s' }}],
        colors: [ '#63B7CF', '#9277AF', '#A6C56D', '#C76560', '#6087B9', '#DB843D', '#92A8CD', '#A47D7C', '#B5CA92' ],
        series: [
          {name: 'close', type: 'area'},
          {name: 'getattr', type: 'area'},
          {name: 'getxattr', type: 'area'},
          {name: 'link', type: 'area'},
          {name: 'mkdir', type: 'area'},
          {name: 'mknod', type: 'area'},
          {name: 'open', type: 'area'},
          {name: 'rename', type: 'area'},
          {name: 'rmdir', type: 'area'},
          {name: 'setattr', type: 'area'},
          {name: 'statfs', type: 'area'},
          {name: 'unlink', type: 'area'}
        ]
      }
    });

    chart_manager.add_chart('iops', 'filesystem', {
      url: 'target/metric/',
      api_params: {kind: 'OST'},
      api_params_callback: api_params_add_filessytem,
      metrics: ["stats_write_bytes","stats_read_bytes"],
      data_callback: function(chart, data) {
        // Generate a number of series objects and return them
        var result = {};
        _.each(data, function(series_data, target_id) {

          var update_data = [];
          _.each(series_data, function(datapoint) {
              var timestamp = new Date(datapoint.ts).getTime();
              var read_bytes = _.isUndefined(datapoint.data.stats_read_bytes)? 0 : datapoint.data.stats_read_bytes;
              var write_bytes =  _.isUndefined(datapoint.data.stats_write_bytes)? 0 : datapoint.data.stats_write_bytes;
              update_data.push([timestamp, read_bytes - write_bytes]);
            });

          var target = ApiCache.get('target', target_id);
          var label;
          if (target) {
            label = target.attributes.label;
          } else {
            label = target_id;
          }
          result[target_id] = {
            id: target_id,
            label: label,
            data: update_data
          };
        });

        return result;
      },
      series_template: {type: 'areaspline'},
      chart_config: {
        chart: {
          renderTo: 'filesystem_ost_read_write'
        },
        title: { text: 'OST Read/Write balance'},
        xAxis: { type:'datetime' },
        yAxis: [{
          title: null,
          labels: {formatter: bytes_rate_formatter}
        }],
        plotOptions: {
          areaspline: {
            stacking: 'normal'
          }
        },
        legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0}
      }
    });

    // switch back to called group
    chart_manager.chart_group(chart_group);
    chart_manager.init();
    return chart_manager;
  }

  function populate_breadcrumb_filesystem(filesystems)
  {
    var selected_filesystem_id;
    if (dashboard_filesystem){
      selected_filesystem_id = dashboard_filesystem.id;
    }

    var filesystem_list_content = "";
    filesystem_list_content = "<option value=''>Select File System</option>";
    _.each(filesystems, function(filesystem) {
      filesystem_list_content += "<option value="+filesystem.id;
      /*jslint eqeq: true */
      if (filesystem.id == selected_filesystem_id) {
        filesystem_list_content += " selected='selected'";
      }
      /*jslint eqeq: false */
      filesystem_list_content += ">" +filesystem.label+"</option>";
    });
    $('#breadcrumb_filesystem').html(filesystem_list_content);
  }

  function populate_breadcrumb_server(servers)
  {
    var selected_server_id;
    if (dashboard_server){
      selected_server_id = dashboard_server.id;
    }

    var server_list_content = "<option value=''>Select Server</option>";
    _.each(servers, function(server) {
      server_list_content += "<option value="+server.id;
      /*jslint eqeq: true */
      if (server.id == selected_server_id) {
        server_list_content += " selected='selected'";
      }
      /*jslint eqeq: false */
      server_list_content += ">" +server.label+"</option>";
    });
    $('#breadcrumb_server').html(server_list_content);
  }

  return {
    init: init,
    setPath: setPath,
    stopCharts: stopCharts
  };
}());
