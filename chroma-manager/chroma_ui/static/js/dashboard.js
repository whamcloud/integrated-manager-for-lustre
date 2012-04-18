//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var Dashboard = function(){
  var initialized = false;
  var chart_manager = null;
  var dashboard_type;
  var dashboard_server;
  var dashboard_target;
  var dashboard_filesystem;
  var polling_enabled = true;
  var time_period;

  function init() {
    function updateUnits(interval_select) {
      var intervalValue = interval_select.val();
      var unitSelectOptions = "";
      if(intervalValue == "")
      {
        unitSelectOptions = "<option value=''>Select</option>";
      }
      else if(intervalValue == "seconds")
      {
        unitSelectOptions = getUnitSelectOptions(61);
      }
      else if(intervalValue == "minutes")
      {
        unitSelectOptions = getUnitSelectOptions(61);
      }
      else if(intervalValue == "hour")
      {
        unitSelectOptions = getUnitSelectOptions(24);
      }
      else if(intervalValue == "day")
      {
        unitSelectOptions = getUnitSelectOptions(32);
      }
      else if(intervalValue == "week")
      {
        unitSelectOptions = getUnitSelectOptions(5);
      }
      else if(intervalValue == "month")
      {
        unitSelectOptions = getUnitSelectOptions(13);
      }
      $("select[id=unitSelect]").html(unitSelectOptions);
    }
    $("select[id=intervalSelect]").change(function()
    {
      updateUnits($(this));
    });

    $("select[id=unitSelect]").change(function(){
      setStartEndTime($(this).prev('font').prev('select').find('option:selected').val(), $(this).find('option:selected').val(), "");
    });

    // Set defaults
    polling_enabled = true;
    time_period = 5 * 60;
    $('select#intervalSelect').attr('value', 'minutes');
    updateUnits($('select#intervalSelect'));
    $('select#unitSelect').attr('value', '5');
    $('input#polling').attr('checked', 'checked');
    
    $("input#polling").click(function()
    {
      if($(this).is(":checked")) {
        polling_enabled = true;
        chart_manager.set_recurring(10);
      } else {
        chart_manager.clear_recurring();
        polling_enabled = false;
      }
    });

    $('#zoomDialog').dialog
    ({
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
      console.log('select target ' + target_id);
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
    if(dashboard_type == "filesystem")
      view_selection_markup += "<option value='filesystem' selected>Filesystems</option>";
    else
      view_selection_markup += "<option value='filesystem'>Filesystems</option>";

    if(dashboard_type == "server")
      view_selection_markup += "<option value='server' selected>Servers</option>";
    else
      view_selection_markup += "<option value='server'>Servers</option>";

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

    console.log(type + " > " + id_1 + " > " + id_2);

    if (id_1) {
      if (type == 'server') {
        dashboard_server = ApiCache.get('server', id_1).toJSON();
        if (id_2) {
          // Showing a target within a server
          dashboard_target = ApiCache.get('target', id_2).toJSON();
          load_target_page();
        } else {
          // Showing a server
          load_server_page();
        }
      } else if (type == 'filesystem') {
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
    breadCrumbHtml += "<li>"+get_server_list_markup()+"</li>";

    breadCrumbHtml += "<li>"+
      "<select id='breadcrumb_target'>"+
      "<option value=''>Select Target</option>";

    Api.get("target/", {"host_id": dashboard_server.id, limit: 0},
      success_callback = function(data)
      {
        var targets = data.objects;
        targets = targets.sort(function(a,b) {return a.label > b.label;})

        var count = 0;
        $.each(targets, function(i, target_info)
        {
          breadCrumbHtml += "<option value='" + target_info.id + "'>" + target_info.label + "</option>"
          ostKindMarkUp = ostKindMarkUp + "<option value="+target_info.id+">"+target_info.kind+"</option>";
          ost_file_system_MarkUp = ost_file_system_MarkUp + "<option value="+target_info.id+">"+target_info.filesystem_id+"</option>";
          count += 1;
        });

        breadCrumbHtml = breadCrumbHtml +
          "</select>"+
          "</li>"+
          "</ul>";
        $("#breadCrumb0").html(breadCrumbHtml);

        $('#ossSummaryTblDiv').show();
        $('#serverSummaryTblDiv').show();
      });

    init_charts('servers');
  }

  function load_target_page()
  {
    dashboard_page('target');

    $('#dashboard_page_global').hide();$('#fileSystemDiv').hide();$('#ossInfoDiv').hide();
    $('#ostInfoDiv').show();

    var breadCrumbHtml = "<ul>"+
      "<li><a href='dashboard/' class='home_icon navigation'>Home</a></li>"+
      "<li>"+get_view_selection_markup()+"</li>";
    if (dashboard_filesystem){
      breadCrumbHtml += "<li><a class='navigation' href='dashboard/filesystem/" + dashboard_filesystem.id + "/''>"+dashboard_filesystem.label+"</a></li>";
    } else {
      breadCrumbHtml += "<li><a class='navigation' href='dashboard/server/" + dashboard_server.id + "/'>"+dashboard_server.label+"</a></li>";
    }

    breadCrumbHtml += "<li>"+dashboard_target.label+"</li>"+
      "</ul>";

    $("#breadCrumb0").html(breadCrumbHtml);

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
        "<td class='greybgcol'>Failover :</td><td class='tblContent greybgcol'>NA</td>" +
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

    if(dashboard_target.kind == 'OST') {
      //ost_Pie_Space_Data($('#ls_ostId').val(), $('#ls_ostName').val(), "", "", "Average", $('#ls_ostKind').val(), spaceUsageFetchMatric, "false");
      //ost_Pie_Inode_Data($('#ls_ostId').val(), $('#ls_ostName').val(), "", "", "Average", $('#ls_ostKind').val(), spaceUsageFetchMatric, "false");
      //ost_Area_ReadWrite_Data($('#ls_ostId').val(), $('#ls_ostName').val(), startTime, endTime, "Average", $('#ls_ostKind').val(), readWriteFetchMatric, "false");
      $("#target_space_usage_container,#target_inodes_container,#target_read_write_container_div").show();
      $("#target_mgt_ops_container_div").hide();
      init_charts('targets_ost');

    }
    else if (dashboard_target.kind == 'MDT') {
      //ost_Area_mgtOps_Data($('#ls_ostId').val(), "false");
      $("#target_space_usage_container,#target_inodes_container,#target_read_write_container_div").hide();
      $("#target_mgt_ops_container_div").show();
      init_charts('targets_mdt');
    }
    else {
      $("#target_space_usage_container,#target_inodes_container,#target_read_write_container_div,#target_mgt_ops_container_div").hide();
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
        targets = targets.sort(function(a,b) {return a.label > b.label;})

        var count = 0;
        $.each(targets, function(i, target_info)
        {
          breadCrumbHtml += "<option value='" + target_info.id + "'>" + target_info.label + "</option>"

          ostKindMarkUp = ostKindMarkUp + "<option value="+target_info.id+">"+target_info.kind+"</option>";

          count += 1;
        });

        breadCrumbHtml = breadCrumbHtml +
          "</select>"+
          "</li>"+
          "</ul>";
        $("#breadCrumb0").html(breadCrumbHtml);
        populate_breadcrumb_filesystem(ApiCache.list('filesystem'), dashboard_filesystem.id);

        $("#ostKind").html(ostKindMarkUp);
      });

    init_charts('filesystem');

    var innerContent = "";
    $('#fileSystemSummaryTbl').html("<tr><td width='100%' align='center' height='180px'>" +
      "<img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' />" +
      "</td></tr>");

    innerContent = innerContent +
      "<tr>" +
      "<td class='greybgcol'>MGS :</td>" +
      "<td class='tblContent greybgcol'>"+dashboard_filesystem.mgt.primary_server_name+"</td>" +
      "<td>&nbsp;</td>" +
      "<td>&nbsp;</td>" +
      "</tr>"+
      "<tr>" +
      "<td class='greybgcol'>MDS:</td>" +
      "<td class='tblContent greybgcol'>"+dashboard_filesystem.mdts[0].primary_server_name+"</td>" +
      "<td>&nbsp;</td>" +
      "<td>&nbsp;</td>" +
      "</tr>"+
      "<tr>" +
      "<td class='greybgcol'>Total OSTs:</td>" +
      "<td class='tblContent txtleft'>"+dashboard_filesystem.osts.length+"</td>" +
      "<td>&nbsp;</td>" +
      "<td>&nbsp;</td>" +
      "</tr>"+
      "<tr>" +
      "<td class='greybgcol'>Total Capacity: </td>" +
      "<td class='tblContent greybgcol'>"+formatBytes(dashboard_filesystem.bytes_total)+" </td>" +
      "<td class='greybgcol'>Total Free:</td>" +
      "<td class='tblContent txtleft'>"+formatBytes(dashboard_filesystem.bytes_free)+"</td>" +
      "</tr>"+
      "<tr>" +
      "<td class='greybgcol'>Files Total: </td>" +
      "<td class='tblContent greybgcol'>"+formatBigNumber(dashboard_filesystem.files_total)+" </td>" +
      "<td class='greybgcol'>Files Free:</td>" +
      "<td class='tblContent txtleft'>"+formatBigNumber(dashboard_filesystem.files_free)+"</td>" +
      "</tr>"+
      "<tr>" +
      "<td class='greybgcol'>Status:</td>";

    $('#fileSystemSummaryTbl').html(innerContent);
  }


  function load_global_page()
  {
    dashboard_page('global');
    var allfileSystemsSummaryContent = "<tr>"+
      "<td align='center' colspan='4'>"+
      "<b>All Filesystems Summary</b></td>" +
      "</tr>"+
      "<tr>"+
      "<td width='25%' align='left' valign='top'>"+
      "<span class='fontStyle style2 style9'><b>File system</b></span></td>"+
      "<td width='5%' align='right' valign='top'>"+
      "<span class='fontStyle style2 style9'><b>OSS</b></span></td>"+
      "<td width='5%' align='right' valign='top' >"+
      "<span class='fontStyle style2 style9'><b>OST</b></span></td>"+
      "<td width='33%' align='right' valign='top' >"+
      "<span class='fontStyle style2 style9'><b>Total Space</b></span></td>"+
      "<td width='33%' align='right' valign='top' >"+
      "<span class='fontStyle style2 style9'><b>Free Space</b></span></td>" +
      "</tr>";

    var breadCrumbHtml = "<ul>" +
    "  <li><a href='dashboard/' class='home_icon navigation'>Home</a></li>" +
    "  <li>" +
    "    <select id='breadcrumb_type'>" +
    "      <option value='filesystem' selected='selected'>File System View</option>" +
    "      <option value='server'>Server View</option>" +
    "    </select>" +
    "  </li>" +
    "  <li>" +
    "    <select id='breadcrumb_filesystem'>" +
    "    </select>" +
    "    <select id='breadcrumb_server'>" +
    "    </select>" +
    "  </li>" +
    "</ul>";

    $('#breadCrumb0').html(breadCrumbHtml);
    if (dashboard_type == 'filesystem') {
      $('#breadcrumb_server').hide();
      populate_breadcrumb_filesystem(ApiCache.list('filesystem'));
    } else if (dashboard_type == 'server') {
      $('#breadcrumb_filesystem').hide();
      populate_breadcrumb_server(ApiCache.list('server'));
    }

    init_charts('dashboard');
  }

  function init_charts(chart_group) {
    /* helper callbacks */
    var api_params_add_filessytem = function(api_params,chart) {
      api_params.filesystem_id = dashboard_filesystem.id;
      return api_params;
    };

    if (!_.isNull(chart_manager)) {
      chart_manager.destroy();
    }
    chart_manager = ChartManager({chart_group: 'dashboard'});
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
        title: { text: 'Server CPU and Memory'},
        xAxis: { type:'datetime' },
        legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0},
        yAxis: [{
          title: { text: 'Percentage' },
          max:100, min:0, startOnTick:false,  tickInterval: 20
        }],
        series: [
          { type: 'line', data: [], name: 'cpu' },
          { type: 'line', data: [], name: 'mem' }
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
            update_data.push([timestamp, ( datapoint.data.stats_read_bytes + datapoint.data.stats_write_bytes )])
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
          }
        });

        return result;
      },
      series_template: {type: 'areaspline'},
      chart_config: {
        chart: {
          renderTo: 'global_ost_bandwidth'
        },
        title: { text: 'OST read/write bandwidth'},
        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'Bytes/s' }}],
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
        title: { text: 'Read/write bandwidth'},
        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'Bytes/s' }, labels: {formatter: function() {
          if (this.value < 0) {
            this.value = this.value * -1;
          }
          var l = "" + formatBytes(this.value, 0);
          if (l[0] == '-') {
            return l.substr(1)
          } else {
            return l;
          }
        }}}],
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
            var current_data = fs_data[0].data
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
        title: { text: 'Space usage'},
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
        yAxis:{max:100, min:0, startOnTick:false, title:{text:'Percentage'}, plotLines: [ { value: 0,width: 1, color: '#808080' } ] },
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
        yAxis: [{title: { text: 'Clients' }}],
        series: [
          { type: 'line', data: [], name: 'Client count' }
        ]
      }
    });

    // oss
    chart_manager.chart_group('servers');
    chart_manager.add_chart('cpu_mem','servers', {
      url: function() { return 'host/' + dashboard_server.id + '/metric/'; },
      api_params: { reduce_fn: 'average' },
      metrics: ["cpu_total", "cpu_user", "cpu_system", "cpu_iowait", "mem_MemFree", "mem_MemTotal"],
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
        },
        function( timestamp, data, index, chart ) {
          var pct_mem  = 100 * ( ( data.mem_MemTotal - data.mem_MemFree )/ data.mem_MemTotal );
          chart.series_data[index].push( [ timestamp, pct_mem ]);
        }
      ],
      chart_config: {
        chart: { renderTo: 'oss_avgReadDiv', width: 500 },
        title: { text: 'Server CPU and Memory'},
        xAxis: { type:'datetime' },
        legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0},
        yAxis: [{
          title: { text: 'Percentage' },
          max:100, min:0, startOnTick:false,  tickInterval: 20
        }],
        series: _.map(
          [ 'user','system','iowait','mem'],
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
        chart: { renderTo: 'oss_avgWriteDiv', width: 500 },
        title: { text: 'Read/write bandwidth'},
        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'Bytes/s' }}],
        series: [
          { type: 'area', name: 'read' },
          { type: 'area', name: 'write' }
        ]
      }
    });

    // ost
    chart_manager.chart_group('targets_ost');
    chart_manager.add_chart('freespace','targets_ost', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/' },
      api_params: {reduce_fn: 'sum', kind: 'OST', group_by: 'filesystem', latest: true},
      metrics: ["kbytestotal", "kbytesfree"],
      snapshot: true,
      snapshot_callback: function(chart, data) {
        var free=0,used=0;
        var totalDiskSpace=0,totalFreeSpace=0;
        if ( _.isObject(data[0])) {
          totalFreeSpace = data[0].data.kbytesfree/1024;
          totalDiskSpace = data[0].data.kbytestotal/1024;
          free = Math.round(((totalFreeSpace/1024)/(totalDiskSpace/1024))*100);
          used = Math.round(100 - free);
        }
        chart.instance.series[0].setData([ ['Free', free], ['Used', used] ]);
      },
      chart_config_callback: function(chart_config) {
        chart_config.title.text = dashboard_target.label + " Space Usage"
        return chart_config;
      },
      chart_config: {
        chart: {
          renderTo: 'target_space_usage_container',
          marginLeft: '50',
          width: '250',
          height: '200',
          borderWidth: 0,
          plotBorderWidth: 0,
          plotShadow: false,
          style:{ width:'100%',  height:'200px' }
        },
        colors: [ '#A6C56D', '#C76560' ],
        title:{ text: '' },
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
      url: function() { return 'target/' + dashboard_target.id + '/metric/' },
      api_params: {reduce_fn: 'sum', kind: 'OST', group_by: 'filesystem', latest: true},
      metrics: ["filestotal", "filesfree"],
      snapshot: true,
      snapshot_callback: function(chart, data) {
        var free=0,used=0;
        var totalFiles=0,totalFreeFiles=0;
        if ( _.isObject(data[0])) {
          totalFiles = data[0].data.filesfree/1024;
          totalFreeFiles = data[0].data.filestotal/1024;
          free = Math.round(((totalFiles/1024)/(totalFreeFiles/1024))*100);
          used = Math.round(100 - free);
        }
        chart.instance.series[0].setData([ ['Free', free], ['Used', used] ]);
      },
      chart_config_callback: function(chart_config) {
        chart_config.title.text = dashboard_target.label + " - Files vs Free Inodes"
        return chart_config;
      },
      chart_config: {
        chart: {
          renderTo: 'target_inodes_container',
          //marginLeft: '50',
          width: '250',
          height: '200',
          borderWidth: 0,
          plotBorderWidth: 0,
          plotShadow: false,
          style:{ width:'100%',  height:'200px' }
        },
        colors: [ '#A6C56D', '#C76560' ],
        title:{ text: '' },
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
      url: function() { return 'target/' + dashboard_target.id + '/metric/' },
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
          renderTo: 'target_read_write_container',
          width: 500
        },
        legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
        title: { text: 'Read vs Writes'},
        tooltip: { formatter: function()  { return ''+ this.series.name +': '+ this.y +''; } },

        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'KB' }}],
        series: [
          { type: 'area', name: 'Read', data: []},
          { type: 'area', name: 'Write',data: []}
        ]
      }
    });

    chart_manager.chart_group('targets_mdt');
    chart_manager.add_chart('mdops', 'targets_mdt', {
      url: function() { return 'target/' + dashboard_target.id + '/metric/' },
      api_params: { reduce_fn: 'sum', kind: 'MDT'},
      metrics: ["stats_close", "stats_getattr", "stats_getxattr", "stats_link",
        "stats_mkdir", "stats_mknod", "stats_open", "stats_rename",
        "stats_rmdir", "stats_setattr", "stats_statfs", "stats_unlink"],
      chart_config: {
        chart: {
          renderTo: 'target_mgt_ops_container',
          width: 480
        },
        tooltip: { formatter: function() { return ''+ this.x +': '+ Highcharts.numberFormat(this.y, 0, ',') +' '; } },

        title: { text: 'Metadata op/s'},
        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'MD op/s' }}],
        colors: [ '#63B7CF', '#9277AF', '#A6C56D', '#C76560', '#6087B9', '#DB843D', '#92A8CD', '#A47D7C',  '#B5CA92' ],
        series: _.map(
          "close getattr getxattr link mkdir mknod open rename rmdir setattr statfs unlink".split(' '),
          function(metric, i) { return { name: metric, type: 'area' }; }
        )
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
        var categories = []
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
            var current_data = fs_data[0].data
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
          renderTo: 'fs_container2'
        },
        title: { text: 'All File System Space Usage'},
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
        yAxis:{max:100, min:0, startOnTick:false, title:{text:'Percentage'}, plotLines: [ { value: 0,width: 1, color: '#808080' } ] },
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
          renderTo: 'fs_container3'
        },
        title: { text: 'Client count'},
        xAxis: { type:'datetime' },
        yAxis: [{
          title: { text: 'Clients' },
          plotLines: [{ value: 0, width: 1, color: '#808080' }]
        }],
        tooltip: { formatter: function() { return 'Time: '+this.x +'No. Of Exports: '+ this.y; } },
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
          renderTo: 'fs_avgCPUDiv'
        },
        title: { text: 'Server CPU and Memory'},
        xAxis: { type:'datetime' },
        legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0},
        yAxis: [{
          title: { text: 'Percentage' },
          max:100,
          min:0,
          startOnTick:false,
          tickInterval: 20
        }],
        series: [
          { type: 'line', data: [], name: 'cpu' },
          { type: 'line', data: [], name: 'mem' }
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
          chart.series_data[index].push( [ timestamp, ( data.stats_read_bytes / 1024 )] );
        },
        function( timestamp, data, index, chart ) {
          chart.series_data[index].push( [ timestamp, - ( data.stats_write_bytes / 1024 ) ] );
        }
      ],
      chart_config: {
        chart: {
          renderTo: 'fs_avgMemoryDiv'
        },
        title: { text: 'Read vs Writes'},
        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'Bytes/s' }}],
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
          renderTo: 'fs_avgReadDiv'
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
            update_data.push([timestamp, ( datapoint.data.stats_read_bytes + datapoint.data.stats_write_bytes ) ])
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
          }
        });

        return result;
      },
      series_template: {type: 'areaspline'},
      chart_config: {
        chart: {
          renderTo: 'fs_iopsSpline'
        },
        title: { text: 'OST read/write bandwidth'},
        xAxis: { type:'datetime' },
        yAxis: [{title: { text: 'Bytes/s' }}],
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

  return {
    init: init,
    setPath: setPath
  }
}();

function getUnitSelectOptions(countNumber)
{
  var unitSelectOptions="<option value=''>Select</option>";
  for(var i=1; i<countNumber; i++)
  {
    unitSelectOptions = unitSelectOptions + "<option value="+i+">"+i+"</option>";
  }
  return unitSelectOptions;
}

function resetTimeInterval()
{
  $("select[id=intervalSelect]").attr("value","");
  $("select[id=unitSelect]").html("<option value=''>Select</option>");
  $("select[id=unitSelect]").attr("value","");
  startTime = "5";
  endTime = "";
}

setStartEndTime = function(timeFactor, startTimeValue, endTimeValue)
{
  endTime = endTimeValue;

  if(timeFactor == "minutes")
    startTime = startTimeValue;
  else if(timeFactor == "hour")
    startTime = startTimeValue * (60);
  else if(timeFactor == "day")
    startTime = startTimeValue * (24 * 60);
  else if(timeFactor == "week")
    startTime = startTimeValue * (7 * 24 * 60);
};

get_server_list_markup = function()
{
  var server_list_markup = "<select id='breadcrumb_server'>";
  _.each(ApiCache.list('server'), function(server) {
    server_list_markup += "<option value="+server.id+">" + server.label + "</option>";
  });

  server_list_markup += "</select>";
  return server_list_markup;
};

function populate_breadcrumb_filesystem(filesystems, selected_filesystem_id)
{
  var filesystem_list_content = "";
  filesystem_list_content = "<option value=''>Select File System</option>";
  _.each(filesystems, function(filesystem) {
    filesystem_list_content += "<option value="+filesystem.id;
    if (filesystem.id == selected_filesystem_id) {
      filesystem_list_content += " selected='selected'";
    }
    filesystem_list_content += ">" +filesystem.label+"</option>";
  });
  $('#breadcrumb_filesystem').html(filesystem_list_content);
}

function populate_breadcrumb_server(servers, selected_server_id)
{
  var server_list_content = "<option value=''>Select Server</option>";
  _.each(servers, function(server) {
    server_list_content += "<option value="+server.id;
    if (server.id == selected_server_id) {
      server_list_content += " selected='selected'";
    }
    server_list_content += ">" +server.label+"</option>";
  });
  $('#breadcrumb_server').html(server_list_content);
}