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


// JSLint option info: http://www.jslint.com/lint.html
/*jslint indent: 2, newcap: true, nomen:true, sloppy: true, undef: true, vars: true, white: true */
/*global _,$ */

var Dashboard = (function() {
  var initialized = false;

  var chart_manager;
  var text_updater;

  var dashboard_type;
  var dashboard_server;
  var dashboard_target;
  var dashboard_filesystem;

  var polling_enabled;
  var time_period;

  var MAXIMUM_OST_ON_DASHBOARD_CHART = 128;

  function stopPollingUpdaters() {
    // FIXME: revise when there is a global chart_manager
    [chart_manager, text_updater].forEach(function (polling_updater) {
      if (polling_updater) {
        polling_updater.destroy();
      }
    });
  }

  function pollingInterval() {
    if (polling_enabled) {
      // scale the polling interval with time_period
      var interval = time_period/60;
      return (interval < 10)? 10 : interval;
    } else {
      return 0;
    }
  }

  function targetSort(a, b) {
    return a.name > b.name ? 1 : -1;
  }

  function init() {

    var intervals = {
      minutes: { max: 60, default: 5, factor:   60          },
      hour:    { max: 24, default: 1, factor: 3600          },
      day:     { max: 31, default: 1, factor: 3600 * 24     },
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
    time_period = 5 * 60;
    polling_enabled = true;
    $('#intervalSelect').val('minutes');
    updateUnits('minutes',5);
    $('input#polling').attr('checked', 'checked');

    $("input#polling").click(function()
    {
      if($(this).is(":checked")) {
        polling_enabled = true;
        chart_manager.set_recurring(pollingInterval());
        chart_manager.render_charts()
      } else {
        polling_enabled = false;
        chart_manager.clear_recurring();
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
      view_selection_markup += "<option value='filesystem' selected>File Systems</option>";
    }
    else {
      view_selection_markup += "<option value='filesystem'>File Systems</option>";
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

    var compileTemplate = angular.element('body').injector().get('compileTemplate');
    var breadCrumbHtml = "<ul>"+
      "<li><a href='dashboard/' class=\"navigation home_icon\" context-tooltip=\"_goto_dashboard\" tooltip-placement=\"right\"><i class='icon-bar-chart'></i></a></li>"+
      "<li>"+get_view_selection_markup()+"</li>";
    breadCrumbHtml += "<li><select id='breadcrumb_server'></select></li>";

    breadCrumbHtml += "<li>"+
      "<select id='breadcrumb_target'>"+
      "<option value=''>Select Target</option>";

    Api.get("target/", {"host_id": dashboard_server.id, limit: 0},
      success_callback = function(data)
      {
        var targets = data.objects;
        targets = targets.sort(targetSort);

        var count = 0;
        $.each(targets, function(i, target_info)
        {
          if (target_info.label == "MGS") { return; }
          breadCrumbHtml += "<option value='" + target_info.id + "'>" + target_info.label + "</option>";
          ostKindMarkUp = ostKindMarkUp + "<option value="+target_info.id+">"+target_info.kind+"</option>";
          ost_file_system_MarkUp = ost_file_system_MarkUp + "<option value="+target_info.id+">"+target_info.filesystem_id+"</option>";
          count += 1;
        });

        breadCrumbHtml = breadCrumbHtml +
          "</select>"+
          "</li>"+
          "</ul>";
        $('#breadcrumbs').html(compileTemplate(breadCrumbHtml));
        populate_breadcrumb_server(ApiCache.list('host'));

        $('#ossSummaryTblDiv').show();
        $('#serverSummaryTblDiv').show();

        // HYD-2012 -- only display the read/write chart if this server has at least one OST
        var hasOst = targets.some(function (target) { return target.kind === 'OST'; });
        var method = (hasOst ? 'show' : 'hide');
        $('#first_server_chart_grid_row')[method]();

      });

    init_charts('servers');
  }

  function load_target_page()
  {
    dashboard_page('target');

    var target_params = "";

    var compileTemplate = angular.element('body').injector().get('compileTemplate');
    var breadCrumbHtml = "<ul>"+
      "<li><a href='dashboard/' class=\"navigation home_icon\" context-tooltip=\"_goto_dashboard\" tooltip-placement=\"right\"><i class='icon-bar-chart'></i></a></li>"+
      "<li>"+get_view_selection_markup()+"</li>";
    if (dashboard_filesystem){
      breadCrumbHtml += "<li><a class='navigation' href='dashboard/filesystem/" + dashboard_filesystem.id + "/''>"+dashboard_filesystem.label+"</a></li>";
      target_params = {"filesystem_id": dashboard_filesystem.id, limit:0};
    } else {
      breadCrumbHtml += "<li><a class='navigation' href='dashboard/server/" + dashboard_server.id + "/'>"+dashboard_server.label+"</a></li>";
      target_params = {"host_id": dashboard_server.id, limit:0};
    }
    breadCrumbHtml += "<li>"+
      "<select id='breadcrumb_target'>"

    Api.get("target/", target_params,
      success_callback = function(data)
      {
        var targets = data.objects;
        targets = targets.sort(targetSort);

        var count = 0;
        $.each(targets, function(i, target_info)
        {
          if (target_info.label == "MGS") { return; }
          breadCrumbHtml += "<option value='" + target_info.id + "'"
          if (target_info.id == dashboard_target.id) {
            breadCrumbHtml += ' selected="selected"'
          }
          breadCrumbHtml +=">" + target_info.label + "</option>";
          count += 1;
        });

        breadCrumbHtml = breadCrumbHtml +
          "</select>"+
          "</li>"+
          "</ul>";
        $('#breadcrumbs').html(compileTemplate(breadCrumbHtml));
      });


    $('#target_name').html(dashboard_target.label);

    if (dashboard_target.filesystem) {
      var innerContent = "";
      $('#ostSummaryTbl').html("<tr><td width='100%' align='center' height='180px'>" +
        "<img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' /></td></tr>");

      var filesystem = ApiCache.get('filesystem', dashboard_target.filesystem_id).toJSON()

      Api.get('target/' + dashboard_target.id + '/metric/',
        {metrics: "filestotal,filesfree,kbytestotal,kbytesfree", latest:true},
        success_callback = function(data) {
          var inode_label = (dashboard_target.kind == 'OST')? "Objects" : "Files";
          var filestotal= 0,filesfree= 0,kbytestotal=0,kbytesfree=0;

          if (_.isObject(data[0])) {
            filestotal = data[0].data.filestotal;
            filesfree = data[0].data.filesfree;
            kbytestotal = data[0].data.kbytestotal;
            kbytesfree = data[0].data.kbytesfree;
          }

          innerContent = innerContent +
            "<tr>" +
            "<td class='greybgcol'>Active Host</td><td class='tblContent greybgcol'>"+dashboard_target.active_host_name+"</td><td>&nbsp;</td><td>&nbsp;</td>" +
            "</tr>"+
            "<tr>" +
            "<td class='greybgcol'>File System :</td>" +
            "<td class='tblContent greybgcol'>"+filesystem.name+"</td>" +
            "<td>&nbsp;</td>" +
            "<td>&nbsp;</td>" +
            "</tr>"+
            "<tr>" +
            "<td class='greybgcol'>Max Space: </td>" +
            "<td class='tblContent greybgcol'>"+formatKBytes(kbytestotal, 4)+" </td>" +
            "<td class='greybgcol'>Free space:</td>" +
            "<td class='tblContent greybgcol'>"+formatKBytes(kbytesfree, 4)+"</td>" +
            "</tr>"+
            "<tr>" +
            "<td class='greybgcol'>Max. "+ inode_label + ": </td>" +
            "<td class='tblContent greybgcol'>"+formatBigNumber(filestotal)+" </td>" +
            "<td class='greybgcol'>Used "+ inode_label + ":</td>" +
            "<td class='tblContent greybgcol'>"+formatBigNumber(filestotal - filesfree)+"</td>" +
            "</tr>";

          $('#ostSummaryTbl').html(innerContent);
        });

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
      $("#target_read_write_container_div").hide();
      $("#target_space_usage_container,#target_mdt_ops_container_div,#target_inodes_container").show();
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

    var compileTemplate = angular.element('body').injector().get('compileTemplate');
    var breadCrumbHtml = "<ul>"+
      "<li><a href='dashboard/' class=\"navigation home_icon\" context-tooltip=\"_goto_dashboard\" tooltip-placement=\"right\"><i class='icon-bar-chart'></i></a></li>"+
      "<li>"+get_view_selection_markup()+"</li>" +
      "<li><select id='breadcrumb_filesystem'></select></li>" +
      "<li>"+
      "<select id='breadcrumb_target'>" + "<option value=''>Select Target</option>";


    Api.get("target/", {"filesystem_id": dashboard_filesystem.id, limit: 0},
      success_callback = function(data)
      {
        var targets = data.objects;
        targets.sort(targetSort);

        var count = 0;
        $.each(targets, function(i, target_info)
        {
          if (target_info.label == "MGS") { return; }
          breadCrumbHtml += "<option value='" + target_info.id + "'>" + target_info.label + "</option>";

          ostKindMarkUp = ostKindMarkUp + "<option value="+target_info.id+">"+target_info.kind+"</option>";

          count += 1;
        });

        breadCrumbHtml = breadCrumbHtml +
          "</select>"+
          "</li>"+
          "</ul>";
        $('#breadcrumbs').html(compileTemplate(breadCrumbHtml));
        populate_breadcrumb_filesystem(ApiCache.list('filesystem'));

        $("#ostKind").html(ostKindMarkUp);
      });

    init_charts('filesystem');
    init_text_updater('filesystem');

    $('#filesystem_name').html(dashboard_filesystem.label);

    $('#fileSystemSummaryTbl').html(
      _.template(
          $('#filesystem_summary_table_template').html(),
          { dashboard_filesystem: dashboard_filesystem }
      )
    );
  }


  function load_global_page()
  {
    dashboard_page('global');

    var compileTemplate = angular.element('body').injector().get('compileTemplate');
    var breadCrumbHtml = "<ul>" +
    "  <li><a href='dashboard/' class=\"navigation home_icon\" context-tooltip=\"_goto_dashboard\" tooltip-placement=\"right\"><i class='icon-bar-chart'></i></a></li>"+
    "  <li>" + get_view_selection_markup() + "</li>" +
    "  </li>" +
    "  <li>" +
    "    <select id='breadcrumb_filesystem'>" +
    "    </select>" +
    "    <select id='breadcrumb_server'>" +
    "    </select>" +
    "  </li>" +
    "</ul>";

    $('#breadcrumbs').html(compileTemplate(breadCrumbHtml));

    if (dashboard_type === 'filesystem') {
      $('#breadcrumb_server').hide();
      populate_breadcrumb_filesystem(ApiCache.list('filesystem'));
    } else if (dashboard_type === 'server') {
      $('#breadcrumb_filesystem').hide();
      populate_breadcrumb_server(ApiCache.list('host'));
    }
    $(this).find('option:selected').val();
    init_charts('dashboard');
    init_text_updater('dashboard');
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


  // TEXT UPDATER

  // helper function to render data to the global filesystem table
  // - dynamically adds/removes filesystems on creation/deletion
  // passed as the update arguement to a text updater (orverrides default)

  function global_filesystem_table_update(snapshot_data) {

    // cleanup. Remove filesystem rows that no longer exist
    $('#global_filesystem_table tr.filesystem_row').each(function() {
      var $filesystem_row = $(this);
      var fs_id = $filesystem_row.data('fs_id');
      if ( fs_id && ! _.has(snapshot_data,fs_id) ) {
        $filesystem_row.remove();
      }
    });

    var template = _.template($('#global_filesystem_table_row_template').html());

    Object.keys(snapshot_data).forEach(function(fs_id) {
      var fs_data = snapshot_data[fs_id]
      var row_selector = '#global_filesystem_table tr.filesystem_row[data-fs_id="'+fs_id+'"]';

      // add new filesystem
      if ( ! $(row_selector).length ) {
        var filesystem = ApiCache.get('filesystem', fs_id);
        $('#global_filesystem_table')
          .find('tbody')
          .append( template({filesystem: filesystem}) );
      }

      // process fs_data
      Object.keys(fs_data).forEach(function (selector) {
        render_text_or_peity(row_selector + ' ' + selector, fs_data[selector]);
      });
    });

  }

  // helper to render peity vs straight text
  function render_text_or_peity(selector, render_data) {
    var $selector = $(selector);
    // text only
    if ( ! _.isObject(render_data) ) {
      $selector.text(render_data);
    }
    // peity charts
    else if ( _.has(render_data, 'peity_chart_type') ) {
      $selector.text(render_data.data).change();
      // peity adds a sibling <canvas> so check; init peity if it's missing
      if ( ! $selector.siblings('canvas').length ) {
        $selector.peity(render_data.peity_chart_type, render_data.peity_config || {});
      }
    }
  }

  /* helper callbacks */
  function api_params_add_filesystem( api_params ) {
    api_params.filesystem_id = dashboard_filesystem.id;
    return api_params;
  }

  function init_text_updater(consumer_group) {
    if ( text_updater ) {
      text_updater.destroy();
    }

    text_updater = TextUpdater({consumer_group: 'dashboard', default_time_boundary: time_period * 1000,
                                  interval_seconds: pollingInterval()});

    // updates client_count in dashboard filesystem table
    text_updater.add_consumer('client_count', 'dashboard', {
      url:'target/metric/',
      api_params: { reduce_fn:'sum', kind:'MDT', group_by: 'filesystem'},
      metrics:["client_count"],
      update: global_filesystem_table_update,
      snapshot_callback: function(consumer, snapshot_data) {
        var filesystem_data = {};
        Object.keys(snapshot_data).forEach(function(fs_id) {
          var fs_data = snapshot_data[fs_id];
          var client_count = fs_data.length ? fs_data[0].data.client_count : '-';
          filesystem_data[fs_id] = { 'td.client_count': client_count };
        });
        return filesystem_data;
      }
    });
    // updates bytes free/total data in dashboard filesystem table + minigraphs!
    text_updater.add_consumer('bytes_data', 'dashboard', {
      url:'target/metric/',
      api_params: { kind: 'OST', reduce_fn:'sum', group_by: 'filesystem'},
      metrics:["kbytestotal", "kbytesfree", "filestotal", "filesfree"],
      update: global_filesystem_table_update,
      snapshot_callback: function(consumer, snapshot_data) {
        var filesystem_data = {};
        _.each(snapshot_data, function(fs_data, fs_id) {
          var result = {};
          if ( fs_data.length ) {
            current_data = fs_data[0].data;

            // plain text
            result['td span.space'] = formatKBytes(current_data.kbytestotal - current_data.kbytesfree) + ' / ' + formatKBytes(current_data.kbytestotal);
            result['td span.inodes'] = formatBigNumber( current_data.filestotal - current_data.filesfree) + ' / ' + formatBigNumber( current_data.filestotal );

            // peity charts
            result['td span.peity_space'] = {
              data: current_data.kbytesfree + '/' + current_data.kbytestotal,
              peity_chart_type: "pie"
            };
            result['td span.peity_inodes'] = {
              data: current_data.filesfree + '/' + current_data.filestotal,
              peity_chart_type: "pie"
            };
          }
          filesystem_data[fs_id] = result;
        });

        return filesystem_data;
      }
    });

    text_updater.consumer_group('filesystem');
    text_updater.add_consumer('client_count', 'filesystem', {
      url:'target/metric/',
      api_params: { reduce_fn:'sum', kind:'MDT' },
      api_params_callback: api_params_add_filesystem,
      metrics:["client_count"],
      render_to: { client_count: '#fileSystemSummaryTbl td.client_count' }
    });
    text_updater.add_consumer('bytes_data', 'filesystem', {
      url:'target/metric/',
      api_params: { kind: 'OST', reduce_fn:'sum' },
      api_params_callback: api_params_add_filesystem,
      metrics:["kbytestotal", "kbytesfree", "filestotal", "filesfree"],
      update: function (snapshot_data) {
        _.each(snapshot_data, function(value,selector) {
          render_text_or_peity(selector, value);
        });
      },
      snapshot_callback: function(consumer, snapshot_data) {

        var result = {};

        if ( ! snapshot_data.length ) {
          return result;
        }

        var current_data = snapshot_data[0].data;

        // plain text
        result['#fileSystemSummaryTbl tr td span.space'] =
          formatKBytes(current_data.kbytestotal - current_data.kbytesfree) + ' / ' + formatKBytes(current_data.kbytestotal);
        result['#fileSystemSummaryTbl tr td span.inodes'] =
          formatBigNumber( current_data.filestotal - current_data.filesfree) + ' / ' + formatBigNumber( current_data.filestotal );

        // peity charts
        result['#fileSystemSummaryTbl tr td span.peity_space'] = {
          data: current_data.kbytesfree + '/' + current_data.kbytestotal,
          peity_chart_type: "pie"
        };
        result['#fileSystemSummaryTbl tr td span.peity_inodes'] = {
          data: current_data.filesfree + '/' + current_data.filestotal,
          peity_chart_type: "pie"
        };

        return result;
      }
    });


    // switch back to called group
    text_updater.consumer_group(consumer_group);
    text_updater.init();
    return text_updater;

  }

  // CHART MANAGER
  function init_charts(chart_group) {

    if ( chart_manager ) {
      chart_manager.destroy();
    }

    // ost_balance chart needs a pre-compiled template for tooltips
    // used by both dashboard and filesystem page
    var ost_balance_tooltip_template = _.template($('#ost_balance_tooltip_template').html());
    var tooltip_template = _.template($('#tooltip_template').html());

    // need to know the number of OSTs so we can customize graph settings BEFORE first data callback
    // will filter if we are on a filesystem detail page
    var ost_targets = _.filter(
      _.filter(
        ApiCache.list('target'),
        function(target) { return target.kind === 'OST'; }
      ),
      function(target) { if( dashboard_filesystem ) { return target.filesystem_id == dashboard_filesystem.id; } else { return 1; } }
    );

    function bytes_tooltip_formatter() {
      var tooltip_data = {
        label : this.points[0].series.autoDateFormat(this.points[0].key),
        points : this.points.map(function(point) {
          return {
            series_name  : point.series.name,
            series_color : point.series.color,
            value        : formatBytes(point.y)
          };
        })
      };
      return tooltip_template( tooltip_data );
    }

    function readwrite_tooltip_formatter() {
      var tooltip_data = {
        label : this.points[0].series.autoDateFormat(this.points[0].key),
        points   : [
          { series_name : this.points[0].series.name, series_color : this.points[0].series.color, value : "%s/s".sprintf(formatBytes(this.points[0].y)) },
          { series_name : this.points[1].series.name, series_color : this.points[1].series.color, value : "%s/s".sprintf(formatBytes(this.points[1].y * -1)) }
        ]
      };
      return tooltip_template( tooltip_data );
    }

    //used by both dashboard and filesystem OST Balance charts as the snapshot_callback
    function ost_balance_snapshot_callback(chart,data) {
      var freeBytes = [];
      var usedBytes = [];
      categories = [];

      _.each(data, function(target_data, target_id) {

        var target = ApiCache.get('target', target_id);

        var name = target ? target.attributes.name : target_id;

        // if no data, assume new
        var free = 100;
        var used = 0;
        var tooltip_data = {
          bytes_free   : '-',
          bytes_used   : '-',
          bytes_total  : '-',
          percent_free : '100%',
          percent_used : '0%'
        };
        tooltip_data.target_name = name;

        // this chart only displays when there's < 128 osts, so we'll nick off
        // the filesystem part of <filesystem>-OST<index> if we're on the dashboard
        // or if there's only one filesystem
        if ( dashboard_filesystem || ApiCache.list('filesystem').length === 1) {
          name = name.replace(/^[^\-]+-/,'');
        }
        categories.push(name);

        if (target_data.length) {
          var current_data = target_data[0].data;

          free = ((current_data.kbytesfree)/(current_data.kbytestotal))*100;
          used = 100 - free;

          tooltip_data.percent_free = Math.round(free) + '%';
          tooltip_data.percent_used = Math.round(used) + '%';
          tooltip_data.bytes_free   = formatKBytes(current_data.kbytesfree,1);
          tooltip_data.bytes_used   = formatKBytes(current_data.kbytestotal - current_data.kbytesfree,1);
          tooltip_data.bytes_total  = formatKBytes(current_data.kbytestotal,1);
        }

        // "tooltip_data" will be added to this.point[0].point.config object in the tooltip callback
        freeBytes.push({ name: name, y: free, tooltip_data: tooltip_data } );
        usedBytes.push(used);
      });

      chart.instance.xAxis[0].setCategories(categories);
      chart.instance.series[0].setData(freeBytes, false);
      chart.instance.series[1].setData(usedBytes, false);
    }

    var cpu_chart_template = {
      url: 'host/metric/',
      api_params: { reduce_fn: 'average', role: 'OSS'},
      metrics: ["cpu_total", "cpu_user", "cpu_system", "cpu_iowait", "mem_MemFree", "mem_MemTotal"],
      series_callbacks: [
        function(timestamp, data, index, chart) {
          var sum_cpu = data.cpu_user + data.cpu_system + data.cpu_iowait;
          var pct_cpu = data.cpu_total ? (100 * sum_cpu) / data.cpu_total : 0.0;
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
          renderTo: 'filesystem_oss_cpu_mem'
        },
        title: { text: 'Object store servers'},
        xAxis: { type:'datetime' },
        legend: {
          enabled: true,
          layout: 'horizontal',
          align: 'center',
          verticalAlign: 'bottom', borderWidth: 0
        },
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
    };

    chart_manager = ChartManager({chart_group: 'dashboard', default_time_boundary: time_period * 1000,
                                  interval_seconds: pollingInterval()});

    chart_manager.add_chart('global_mds_cpu_mem', 'dashboard',
      $.extend(true, {}, cpu_chart_template, {
        api_params: {role: "MDS"},
        chart_config: {
          chart: {
            renderTo: 'global_mds_cpu_mem'
          },
          title: {
            text: "Metadata servers"
          },
          tooltip: { valueSuffix: '%', }
        }
      }));

    chart_manager.add_chart('global_oss_cpu_mem', 'dashboard',
      $.extend(true, {}, cpu_chart_template, {
        api_params: {role: "OSS"},
        chart_config: {
          chart: {
            renderTo: 'global_oss_cpu_mem'
          },
          title: {
            text: "Object storage servers"
          },
          tooltip: { valueSuffix: '%', }
        }
      }));

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
          '#B5CA92',
          '#f87d45',
          '#f8457d',
          '#7d45f8'
        ],
        plotOptions: {
          area: {
            lineWidth: 0.0
          }
        },
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
        tooltip: { formatter: readwrite_tooltip_formatter },
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

    // if there's more than one filesystem, we want the old freespace chart
    if ( ost_targets.length > MAXIMUM_OST_ON_DASHBOARD_CHART ) {

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
            categories.push('Bytes | <em>' + name + '</em> | Files');

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
            renderTo: 'global_usage_or_balance',
            zoomType: ''
          },
          title: { text: 'Percent Capacity Used'},
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
          xAxis:{categories: [], labels: {align: 'center', style: {fontSize: '8px', fontWeight: 'regular'}}},
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
    }
    // else, we want the OST Balance chart
    else {

      chart_manager.add_chart('ost_balance', 'dashboard', {
        url: 'target/metric/',
        api_params: { kind: 'OST', latest: true},
        metrics: ["kbytestotal", "kbytesfree"],
        snapshot: true,
        snapshot_callback: ost_balance_snapshot_callback,
        chart_config: {
          chart: {
            renderTo: 'global_usage_or_balance',
            zoomType: ''
          },
          title: { text: 'OST Balance'},
          series: [
            { type: 'column', stack: 0, name: 'Free bytes'},
            { type: 'column', stack: 0, name: 'Used bytes'},
          ],
          plotOptions: {
            column: {
              stacking: 'normal',
              pointPadding: 0.05,
              borderWidth: 1,
              borderRadius: 3
            }
          },
          xAxis:{
            categories: [],
            tickmarkPlacement: 'on',
            // labels get too busy and overlap past 10
            labels: ost_targets.length > 10 ? false : {
              align: 'center',
              style: { fontSize: '8px', fontWeight: 'regular'}
            }
          },
          yAxis:{
            max:100, min:0, startOnTick:false,
            title:null,
            labels: {formatter: percentage_formatter},
            plotLines: [ { value: 0,width: 1, color: '#808080' } ]
          },
          tooltip: {
            formatter: function() {
              return ost_balance_tooltip_template(this.points[0].point.config.tooltip_data);

            }
          },
          labels:{ items:[{html: '',style:{left: '40px',top: '8px',color: 'black'}}]},
          colors: [ '#A6C56D', '#C76560' ]
        }
      });
    }

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
        ),
        tooltip: { valueSuffix: '%', }
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
        ),
        tooltip: { formatter: bytes_tooltip_formatter }
      }
    });

    chart_manager.add_chart('readwrite', 'servers', {
      url: function() { return 'target/metric/'; },
      api_params: { reduce_fn: 'sum', kind: 'OST'},
      api_params_callback: function(api_params, chart) { api_params.host_id = dashboard_server.id; return api_params; },
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
        ],
        tooltip: { formatter: readwrite_tooltip_formatter }
      }
    });

    // ost
    chart_manager.chart_group('targets_ost');
    chart_manager.add_chart('freespace','targets_ost', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/'; },
      api_params: {},
      metrics: ["kbytestotal", "kbytesfree"],
      data_callback: function(chart, data) {
        // Generate a number of series objects and return them
        var result = {};
        var update_data = [];
        _.each(data, function(point, target_id) {
          usedPercent = (point.data.kbytestotal - point.data.kbytesfree)/point.data.kbytestotal * 100;
          update_data.push([new Date(point.ts).getTime(), usedPercent])
        });
        result[0] = {
          id: 0,
          label: "Space Used",
          data: update_data
        }
        return result;
      },
      series_template: {type: 'area'},
      chart_config: {
        chart: {
          renderTo: 'target_space_usage_container',
          plotShadow: false
        },
        colors: [ '#C76560' ],
        title:{ text: 'Space Usage'},
        tooltip: {valueSuffix: '%'},
        zoomType: 'xy',
        xAxis: { type:'datetime' },
        yAxis: [{
          max:100, min:0, startOnTick:false,  tickInterval: 20,
          title: null,
          labels: {formatter: percentage_formatter}
        }],
        plotOptions: {
          area: {
            stacking: null
          }
        }
      }
    });

    chart_manager.add_chart('inode','targets_ost', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/'; },
      api_params: {},
      metrics: ["filestotal", "filesfree"],
      data_callback: function(chart, data) {
        // Generate a number of series objects and return them
        var result = {};
        var update_data = [];
        _.each(data, function(point, target_id) {
          usedPercent = (point.data.filestotal - point.data.filesfree)/point.data.filestotal * 100;
          update_data.push([new Date(point.ts).getTime(), usedPercent])
        });
        result[0] = {
          id: 0,
          label: "Objects Used",
          data: update_data
        }
        return result;
      },
      series_template: {type: 'area'},
      chart_config: {
        chart: {
          renderTo: 'target_inodes_container',
          plotShadow: false
        },
        colors: [ '#C76560' ],
        title:{ text: 'Object Usage'},
        tooltip: {valueSuffix: '%'},
        zoomType: 'xy',
        xAxis: { type:'datetime' },
        yAxis: [{
          max:100, min:0, startOnTick:false,  tickInterval: 20,
          title: null,
          labels: {formatter: percentage_formatter}
        }],
        plotOptions: {
          area: {
            stacking: null
          }
        }
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

        xAxis: { type:'datetime' },
        yAxis: [{
          title: null,
          labels: {formatter: bytes_rate_formatter}
        }],
        series: [
          { type: 'area', name: 'Read', data: []},
          { type: 'area', name: 'Write',data: []}
        ],
        tooltip: { formatter: readwrite_tooltip_formatter }
      }
    });

    chart_manager.chart_group('targets_mdt');
    chart_manager.add_chart('freespace','targets_mdt', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/'; },
      api_params: {},
      metrics: ["kbytestotal", "kbytesfree"],
      data_callback: function(chart, data) {
        // Generate a number of series objects and return them
        var result = {};
        var update_data = [];
        _.each(data, function(point, target_id) {
          usedPercent = (point.data.kbytestotal - point.data.kbytesfree)/point.data.kbytestotal * 100;
          update_data.push([new Date(point.ts).getTime(), usedPercent])
        });
        result[0] = {
          id: 0,
          label: "Space Used",
          data: update_data
        }
        return result;
      },
      series_template: {type: 'area'},
      chart_config: {
        chart: {
          renderTo: 'target_space_usage_container',
          plotShadow: false
        },
        colors: [ '#C76560' ],
        title:{ text: 'Space Usage'},
        tooltip: {valueSuffix: '%'},
        zoomType: 'xy',
        xAxis: { type:'datetime' },
        yAxis: [{
          max:100, min:0, startOnTick:false,  tickInterval: 20,
          title: null,
          labels: {formatter: percentage_formatter}
        }],
        plotOptions: {
          area: {
            stacking: null
          }
        }
      }
    });
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
          '#B5CA92',
          '#f87d45',
          '#f8457d',
          '#7d45f8'
        ],
        plotOptions: {
          area: {
            lineWidth: 0.0
          }
        },
        series: _.map(
          ['close','getattr','getxattr','link','mkdir','mknod','open','rename','rmdir','setattr','statfs','unlink'],
          function(metric, i) { return { name: metric, type: 'area' }; }
        )
      }
    });

    chart_manager.add_chart('inode','targets_mdt', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/'; },
      api_params: {},
      metrics: ["filestotal", "filesfree"],
      data_callback: function(chart, data) {
        // Generate a number of series objects and return them
        var result = {};
        var update_data = [];
        _.each(data, function(point, target_id) {
          usedPercent = (point.data.filestotal - point.data.filesfree)/point.data.filestotal * 100;
          update_data.push([new Date(point.ts).getTime(), usedPercent])
        });
        result[0] = {
          id: 0,
          label: "Files Used",
          data: update_data
        }
        return result;
      },
      series_template: {type: 'area'},
      chart_config: {
        chart: {
          renderTo: 'target_inodes_container',
          plotShadow: false
        },
        colors: [ '#C76560' ],
        title:{ text: 'File Usage'},
        tooltip: {valueSuffix: '%'},
        zoomType: 'xy',
        xAxis: { type:'datetime' },
        yAxis: [{
          max:100, min:0, startOnTick:false,  tickInterval: 20,
          title: null,
          labels: {formatter: percentage_formatter}
        }],
        plotOptions: {
          area: {
            stacking: null
          }
        }
      }
    });

    chart_manager.chart_group('filesystem');
    chart_manager.add_chart('ost_balance', 'filesystem', {
      url: 'target/metric/',
      api_params: { kind: 'OST', latest: true},
      api_params_callback: api_params_add_filesystem,
      metrics: ["kbytestotal", "kbytesfree"],
      snapshot: true,
      snapshot_callback: ost_balance_snapshot_callback,
      chart_config: {
        chart: {
          renderTo: 'filesystem_ost_balance',
          zoomType: ''
        },
        title: { text: 'OST Balance'},
        series: [
          { type: 'column', stack: 0, name: 'Free bytes'},
          { type: 'column', stack: 0, name: 'Used bytes'},
        ],
        plotOptions: {
          column: {
            stacking: 'normal',
            pointPadding: 0.05,
            borderWidth: 1,
            borderRadius: 3
          }
        },
        xAxis:{
          categories: [],
          tickmarkPlacement: 'on',
          // labels get too busy and overlap past 10
          labels: ost_targets.length > 10 ? false : {
            align: 'center',
            style: { fontSize: '8px', fontWeight: 'regular'}
          }
        },
        yAxis:{
          max:100, min:0, startOnTick:false,
          title:null,
          labels: {formatter: percentage_formatter},
          plotLines: [ { value: 0,width: 1, color: '#808080' } ]
        },
        tooltip: {
          formatter: function() {
            return ost_balance_tooltip_template(this.points[0].point.config.tooltip_data);
          }
        },
        labels:{ items:[{html: '',style:{left: '40px',top: '8px',color: 'black'}}]},
        colors: [ '#A6C56D', '#C76560' ]
      }
    });

    chart_manager.add_chart('filesystem_oss_cpu_mem','filesystem',
      $.extend(true, {}, cpu_chart_template, {
        api_params: {role: "OSS"},
        api_params_callback: api_params_add_filesystem,
        chart_config: {
          chart: {
            renderTo: 'filesystem_oss_cpu_mem'
          },
          title: {
            text: "Object storage servers"
          },
          tooltip: { valueSuffix: '%' }
        }
      }));

    chart_manager.add_chart('filesystem_mds_cpu_mem','filesystem',
      $.extend(true, {}, cpu_chart_template, {
        api_params: {role: "MDS"},
        api_params_callback: api_params_add_filesystem,
        chart_config: {
          chart: {
            renderTo: 'filesystem_mds_cpu_mem'
          },
          title: {
            text: "Metadata server"
          },
          tooltip: { valueSuffix: '%' }
        }
      }));

    chart_manager.add_chart('readwrite','filesystem', {
      url: 'target/metric/',
      api_params: { reduce_fn: 'sum', kind: 'OST'},
      api_params_callback: api_params_add_filesystem,
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
        series: [
          { type: 'area', name: 'read' },
          { type: 'area', name: 'write' }
        ],
        tooltip: { formatter: readwrite_tooltip_formatter }
      }
    });
    chart_manager.add_chart('mdops','filesystem', {
      url: 'target/metric/',
      api_params: { reduce_fn: 'sum', kind: 'MDT'},
      api_params_callback: api_params_add_filesystem,
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
        colors: [
          '#63B7CF',
          '#9277AF',
          '#A6C56D',
          '#C76560',
          '#6087B9',
          '#DB843D',
          '#92A8CD',
          '#A47D7C',
          '#B5CA92',
          '#f87d45',
          '#f8457d',
          '#7d45f8'
        ],
        plotOptions: {
          area: {
            lineWidth: 0.0
          }
        },
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
    stopPollingUpdaters: stopPollingUpdaters
  };
}());
