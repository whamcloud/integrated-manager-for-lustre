//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

/*******************************************************************************
 * File name: custom_dasboard.js
 * Description: Common functions required by dashboard
 * ------------------ Data Loader functions--------------------------------------
 * 1) loadView(key)
 * 2) load_breadcrumbs
 * 4) $("select[id=intervalSelect]").change();
 * 5) getUnitSelectOptions(countNumber)
 * 6) resetTimeInterval
 * 7) $("select[id=unitSelect]").change();
 * 8) setStartEndTime(timeFactor, startTimeValue, endTimeValue)
 * 9) loadLandingPage
 * 10) $("#fsSelect").change();
 * 11) loadFSContent(fsId)
 * 12) $("#ossSelect").live('change');
 * 13) loadOSSContent(fsId, fsName, ossId, ossName);
 * 14) $("#ostSelect").live('change');
 * 15) loadOSTContent(fsId, fsName, ossName, ostId, ostName);
 * 17) $("#heatmap_parameter_select").change();
 * 18) reloadHeatMap(fetchmetric);
/*****************************************************************************/
var server_list_content = "";

/********************************************************************************
// Function to populate landing page 
/********************************************************************************/

/******************************************************************************
 * Function to load breadcrumb
******************************************************************************/
  load_breadcrumbs = function()
  {		
    $("#breadCrumb0").jBreadCrumb();
    $("#fsSelect").attr("value", $("#ls_fsId").val());
    $("#serverSelect").attr("value", $("#ls_ossId").val());
  }
/******************************************************************************
 * Function for showing time interval units
******************************************************************************/

var Dashboard = function(){
  var initialized = false;

  function init() {
    $("select[id=intervalSelect]").change(function()
    {
      var intervalValue = $(this).val();
      var unitSelectOptions = "";
      if(intervalValue == "")
      {
        unitSelectOptions = "<option value=''>Select</option>";
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
    });

    $("select[id=unitSelect]").change(function(){
      setStartEndTime($(this).prev('font').prev('select').find('option:selected').val(), $(this).find('option:selected').val(), "");
    });
    
    $("input[id *= polling_element]").click(function()
    {
      if($(this).is(":checked"))
      {
        isPollingFlag = true;
        initiatePolling();
      }
      else
      {
        isPollingFlag = false;
        clearAllIntervals();
      }
    });

    /******************************************************************************
     * Function to show zoom popup dialog
    ******************************************************************************/  
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
        },
      }
    });

    initialized = true;
  }

 function loadView(key)
 {
   if (!initialized) {
     init();
   }

   switch (key) 
   {
     case "#fs":
       window.location.hash =  "fs";
       loadFSContent($('#ls_fsId').val(), $('#ls_fsName').val());
       break;
     case "#oss":
       window.location.hash =  "oss";
       loadOSSContent($('#ls_fsId').val(), $('#ls_fsName').val(), $('#ls_ossId').val(), $('#ls_ossName').val());
       break;
     case "#ost":
       window.location.hash =  "ost";
       loadOSTContent($('#ls_fsId').val(), $('#ls_fsName').val(), $('#ls_ossName').val(), $('#ls_ostId').val(), $('#ls_ostName').val(), $('#ls_ostKind').val());
       break;

     default:
       loadLandingPage();
   }
 };

  return {
    init: init,
    loadView: loadView
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
/*******************************************************************************
 * Function to reset options of the time interval and units selectbox
********************************************************************************/
  function resetTimeInterval()
  {
    $("select[id=intervalSelect]").attr("value","");
    $("select[id=unitSelect]").html("<option value=''>Select</option>");
    $("select[id=unitSelect]").attr("value","");
    startTime = "5";
    endTime = "";
  }
/*******************************************************************************
 * Function to show unit options on selection of time interval
********************************************************************************/

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

    if(! $('#dashboard_page_global').is(':hidden'))
      loadLandingPageGraphs();
    else if(! $('#fileSystemDiv').is(':hidden'))
      loadFileSytemGraphs();
    else if(! $('#ossInfoDiv').is(':hidden'))
      loadServerGraphs();
    else if(! $('#ostInfoDiv').is(':hidden'))
      loadTargetGraphs();
  }

  initiatePolling = function(){
    if(! $('#dashboard_page_global').is(':hidden'))
      initDashboardPolling();
    else if(! $('#fileSystemDiv').is(':hidden'))
      initFileSystemPolling();
    else if(! $('#ossInfoDiv').is(':hidden'))
      initOSSPolling();
    else if(! $('#ostInfoDiv').is(':hidden'))
      initOSTPolling();
  }
/******************************************************************************
 * Function to load landing page
******************************************************************************/
  loadLandingPage = function()
  {     	
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

    $('#dashboard_page_global').show();
    updateChartSizes();

    Api.get("filesystem", {limit: 0},
      success_callback = function(data)
      {
        $('#allFileSystemSummaryTbl').dataTable({
          "aoColumns": [
                        { "sClass": 'txtleft'},
                        { "sClass": 'txtright'},
                        { "sClass": 'txtright'},
                        { "sClass": 'txtright'}
                      ],
                      "iDisplayLength":5,
                      "bRetrieve":true,
                      "bFilter":false,
                      "bLengthChange": false,
                      "bAutoWidth": true,
                      "bSort": false,
                      "bJQueryUI": true
                    }).fnClearTable();
        
        $.each(data.objects, function(resKey, resValue) 
        {

          $('#allFileSystemSummaryTbl').dataTable().fnAddData([
            resValue.name,
            resValue.osts.length,
            formatBytes(resValue.bytes_total),
            formatBytes(resValue.bytes_free),
          ]);
        });

        populateFsSelect(data.objects)
        
        load_breadcrumbs();
      });

      init_charts_global();
  }
  
  $("#selectView").live('change', function ()
  {
    showView($(this).val());
  });
  
  showView = function(view_value)
  {
    var breadCrumbHtml = "<ul style='float: left;'>"+
    "<li><a href='/dashboard'>Home</a></li>"+
    "<li>"+get_view_selection_markup()+"</li>"+
    "<li>" +
    "<select id='fsSelect' style='display:none'>"+
    "</select>" +
    "<select id='serverSelect' style='display:none'>"+
    "</select>" +
    "</li>"+
    "</ul>";
    $("#breadCrumb0").html(breadCrumbHtml);
    
    loadLandingPage();
    $('#fileSystemDiv').hide();$('#ossInfoDiv').hide();$('#ostInfoDiv').hide();

    $('#dashboard_page_global').show();

    if(view_value == "filesystem_view")
    {
      $("#fsSelect").css("display","block");
      $("#serverSelect").css("display","none");
    }
    else if(view_value == "server_view")
    {
      server_list_content = "";
      server_list_content += "<option value=''>Select Server</option>";
      Api.get("host/", {limit: 0}, 
        success_callback = function(data)
        {
          $.each(data.objects, function(i, host)
          {
            server_list_content += "<option value="+host.id+">" + host.label + "</option>";
          });
          $("#serverSelect").html(server_list_content);
          $("#fsSelect").css("display","none");
          $("#serverSelect").css("display","block");
          
          $('#ls_fsId').attr("value", "");
          $('#ls_ossId').attr("value", "");
          
          load_breadcrumbs();
        });
    }
  }
/*****************************************************************************
 *  Function to populate info on file system dashboard page
******************************************************************************/
  $("#fsSelect").live('change', function ()
  {
    if($(this).val()!="")
    {
      loadFSContent($(this).val(), $(this).find('option:selected').text());
    }
  });         

  loadFSContent = function(fsId, fsName)
  {
    $('#dashboard_page_global').hide();$('#ossInfoDiv').hide();$('#ostInfoDiv').hide();
    $('#fileSystemDiv').show();
    updateChartSizes();
    var ostKindMarkUp = "<option value=''></option>";
    
    var breadCrumbHtml = "<ul>"+
    "<li><a href='/dashboard'>Home</a></li>" +
    "<li>"+get_view_selection_markup()+"</li>" +
    "<li><select id=\"fsSelect\"></select></li>" +
    "<li>"+
    "<select id='ostSelect'>"+
    "<option value=''>Select Target</option>";

    Api.get("filesystem", {limit: 0},
      success_callback = function(data) {
        populateFsSelect(data.objects);
      }
    );

    Api.get("target/", {"filesystem_id": fsId, limit: 0}, 
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
        load_breadcrumbs();

        $("#ostKind").html(ostKindMarkUp);
      });

    resetTimeInterval();

		    // 2011-10-17 19:56:58.720036  2011-10-17 19:46:58.720062
    fs_Bar_SpaceUsage_Data(fsId, startTime, endTime, "Average", "OST", spaceUsageFetchMatric, false);

    fs_Line_connectedClients_Data(fsId, startTime, endTime, "Average", clientsConnectedFetchMatric, false);

    fs_LineBar_CpuMemoryUsage_Data(fsId, startTime, endTime, "Average", "OST", cpuMemoryFetchMatric, false);

    fs_Area_ReadWrite_Data(fsId, startTime, endTime, "Average", "OST", readWriteFetchMatric, false);

    fs_Area_mdOps_Data(fsId, startTime, endTime, "Average", "MDT", mdOpsFetchmatric, false);

    fs_AreaSpline_ioOps_Data('false');

    clearAllIntervals();

    loadFileSystemSummary(fsId);
   
    $('#ls_fsId').attr("value",fsId);$('#ls_fsName').attr("value",fsName);
    window.location.hash =  "fs";
   
  }

  $("#serverSelect").live('change', function ()
  {
    if($(this).val()!="")
    {
      var host_id = $(this).val();
      Backbone.history.navigate("/dashboard/server/" + host_id + "/");
      loadOSSContent($('#ls_fsId').val(), $('#ls_fsName').val(), $(this).val(), $(this).find('option:selected').text());
    }   
  });
  
  $("#ossSelect").live('change', function ()
  {
    if($(this).val()!="")
    {
      loadOSSContent($('#ls_fsId').val(), $('#ls_fsName').val(), $(this).val(), $(this).find('option:selected').text());
    }	
  });
		
  loadOSSContent = function(fsId, fsName, ossId, ossName)
  {
    $('#dashboard_page_global').hide();$('#fileSystemDiv').hide();$('#ostInfoDiv').hide();
    $('#ossInfoDiv').show();
    updateChartSizes();
    var ostKindMarkUp = "<option value=''></option>";
    var ost_file_system_MarkUp = "<option value=''></option>";
    
    var breadCrumbHtml = "<ul>"+
    "<li><a href='/dashboard'>Home</a></li>"+
    "<li>"+get_view_selection_markup()+"</li>";
    if(fsId == "")
    {
      breadCrumbHtml += "<li>"+get_server_list_markup()+"</li>";
    }
    else
    {
      breadCrumbHtml +="<li><a href='#fs' onclick='showFSDashboard()'>"+fsName+"</a></li>"+
      "<li>"+ossName+"</li>";
    }
    breadCrumbHtml += "<li>"+
    "<select id='ostSelect'>"+
    "<option value=''>Select Target</option>";

    var file_systems_ids = new Array();
    var file_count = 0;
    
    Api.get("target/", {"host_id": ossId, limit: 0}, 
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
          
          if(target_info.filesystem_id != null)
          {
            if(!find_file_system_id(file_systems_ids, target_info.filesystem_id))
              file_systems_ids.push(target_info.filesystem_id);
          }
  
          count += 1; 
        });
        
        breadCrumbHtml = breadCrumbHtml +      	
        "</select>"+
        "</li>"+
        "</ul>";
        $("#breadCrumb0").html(breadCrumbHtml);
        load_breadcrumbs();

        $("#ostKind").html(ostKindMarkUp);
        $("#ost_file_system").html(ost_file_system_MarkUp);
        
        $('#ossSummaryTblDiv').show();
        $('#serverSummaryTblDiv').show();
      });

    resetTimeInterval();

    oss_LineBar_CpuMemoryUsage_Data(ossId, startTime, endTime, "Average", cpuMemoryFetchMatric, 'false');

    oss_Area_ReadWrite_Data(fsId, startTime, endTime, "Average", "OST", readWriteFetchMatric, 'false');

    clearAllIntervals();

    $('#ls_ossId').attr("value",ossId);$('#ls_ossName').attr("value",ossName);
    window.location.hash =  "oss";
  }
  
  find_file_system_id = function(file_systems_ids, file_system_id)
  {
    for(var x=0; x<file_systems_ids.length; x++)
    {
      if(file_systems_ids[x] == file_system_id)
      {
        return true;
      }
    }
  }
/*******************************************************************************
 * Function to populate info on ost dashboard page
********************************************************************************/
  $("#ostSelect").live('change', function ()
  {
    if($(this).val()!="")
    {
      $("#ostKind").attr("value",$(this).val());
      var ostKind = $("#ostKind").find('option:selected').text();
      
      if($('#ls_fsId').val() == "")
      {
        $("#ost_file_system").attr("value",$(this).val());
      }
      
      loadOSTContent($('#ls_fsId').val(), $('#ls_fsName').val(), $('#ls_ossName').val(), $(this).val(), $(this).find('option:selected').text(), ostKind);
    }	
  });

  loadOSTContent = function(fsId, fsName, ossName, ostId, ostName, ostKind)
  {
    $('#dashboard_page_global').hide();$('#fileSystemDiv').hide();$('#ossInfoDiv').hide();
    $('#ostInfoDiv').show();
    updateChartSizes();
    var breadCrumbHtml = "<ul>"+
    "<li><a href='/dashboard'>Home</a></li>"+
    "<li>"+get_view_selection_markup()+"</li>";
    if(fsId == "")
    {
      breadCrumbHtml += "<li><a href='#oss' onclick='showOSSDashboard()'>"+ossName+"</a></li>";
      fsId =  $("#ost_file_system").find('option:selected').text();
    }
    else
    {
      breadCrumbHtml += "<li><a href='#fs' onclick='showFSDashboard()'>"+fsName+"</a></li>";
      //"<li><a href='#oss' onclick='showOSSDashboard()'>"+ossName+"</a></li>";
    }
    
    breadCrumbHtml += "<li>"+ostName+"</li>"+
    "</ul>";

    $("#breadCrumb0").html(breadCrumbHtml);
    load_breadcrumbs();

    resetTimeInterval();

    $('#ls_ostId').attr("value",ostId);$('#ls_ostName').attr("value",ostName);$('#ls_ostKind').attr("value",ostKind);
    window.location.hash =  "ost";
    
    clearAllIntervals();
    
    if(fsId > 0)
    {
      loadOSTSummary(fsId);
    }
    else
    {
      $('#ostSummaryTbl').html("");
    }
    
    loadTargetGraphs();
  };

		  
/******************************************************************************
 * Function to get markup for breadcrumb view selection
******************************************************************************/
  get_view_selection_markup = function()
  {
    var view_selection_markup = "<select id='selectView'>";
    if($("#selectView").val() == "filesystem_view")
      view_selection_markup += "<option value='filesystem_view' selected>File System View</option>";
    else
      view_selection_markup += "<option value='filesystem_view'>File System View</option>";
    
    if($("#selectView").val() == "server_view")
      view_selection_markup += "<option value='server_view' selected>Server View</option>";
    else
      view_selection_markup += "<option value='server_view'>Server View</option>";
    
    view_selection_markup += "</select>";
    return view_selection_markup;
  }
  
  get_server_list_markup = function()
  {
    var server_list_markup = "<select id='serverSelect'>";
    server_list_markup += server_list_content;
    server_list_markup += "</select>";
    return server_list_markup;
  }

function populateFsSelect(filesystems)
{
  var filesystem_list_content = "";
  $.each(filesystems, function(i, filesystem) {
    filesystem_list_content = "<option value=''>Select File System</option>";
    filesystem_list_content += "<option value="+filesystem.id+">"+filesystem.name+"</option>";
  });
  $('#fsSelect').html(filesystem_list_content);
}

function init_charts_global() {
  /* Set up charts for dashboard_page_global */
  var chart_manager = ChartManager({chart_group: 'dashboard'});
  chart_manager.add_chart('db_line_cpu_mem', 'dashboard', {
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
        renderTo: 'global_cpu_mem',
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
    url: 'target/metric',
    api_params: {kind: 'OST'},
    metrics: ["stats_write_bytes"],
    data_callback: function(chart, data) {
      // Generate a number of series objects and return them
      var result = {};
      _.each(data, function(series_data, target_id) {
        var update_data = [];
        _.each(series_data, function(datapoint) {
          var timestamp = new Date(datapoint.ts).getTime();
          update_data.push([timestamp, datapoint.data.stats_write_bytes])
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
        renderTo: 'global_ost_bandwidth',
      },
      title: { text: 'OST write bandwidth'},
      xAxis: { type:'datetime' },
      yAxis: [{title: { text: 'Bytes/s' }},],
      plotOptions: {
        areaspline: {
          stacking: 'normal',
        }
      },
      legend: { enabled: true, layout: 'vertical', align: 'right', verticalAlign: 'middle', x: 0, y: 10, borderWidth: 0},
    }
  });

  chart_manager.add_chart('mdops', 'dashboard', {
    url: 'target/metric',
    api_params: { reduce_fn: 'sum', kind: 'MDT'},
    metrics: ["stats_close", "stats_getattr", "stats_getxattr", "stats_link", 
              "stats_mkdir", "stats_mknod", "stats_open", "stats_rename", 
              "stats_rmdir", "stats_setattr", "stats_statfs", "stats_unlink"],
    chart_config: {
      chart: {
          renderTo: 'global_metadata_ops',
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
    url: 'target/metric',
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
          renderTo: 'global_read_write',
      },
      title: { text: 'Read/write bandwidth'},
      xAxis: { type:'datetime' },
      yAxis: [{title: { text: 'Bytes/s' }}],
      series: [
          { type: 'area', name: 'read' },
          { type: 'area', name: 'write' }
      ]
    }
  });

  chart_manager.add_chart('freespace', 'dashboard', {
    url: 'target/metric',
    api_params: {reduce_fn: 'sum', kind: 'OST', group_by: 'filesystem', latest: true},
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
          renderTo: 'global_usage',
      },
      title: { text: 'Space usage'},
      series: [
          { type: 'column', stack: 0, name: 'Free bytes'},
          { type: 'column', stack: 0, name: 'Used bytes'},
          { type: 'column', stack: 1, name: 'Free files'},
          { type: 'column', stack: 1, name: 'Used files'},
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
    url: 'target/metric',
    api_params: { reduce_fn: 'sum', kind: 'MDT'},
    metrics: ["client_count"],
    chart_config: {
      chart: {
        renderTo: 'global_client_count',
      },
      title: { text: 'Client count'},
      xAxis: { type:'datetime' },
      yAxis: [{title: { text: 'Clients' }}],
      series: [
        { type: 'line', data: [], name: 'Client count' },
      ]
    }
  });

  chart_manager.init();
  return chart_manager;
};
