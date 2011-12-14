/**************************************************************************
 * File Name - custome_oss.js
 * Description - Contains function to plot pie, line and bar charts on OSS Screen
 * ---------------------Data Loaders function-------------------------------
 * 1) oss_LineBar_CpuMemoryUsage_Data(fsId, sDate, endDate, dataFunction, fetchMetrics, isZoom)
 * 2) oss_Area_ReadWrite_Data(fsId, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
 * 3) loadOSSUsageSummary(fsId)
 * 4) initOSSPolling
******************************************************************************
 * API URL's for all the graphs on OSS dashboard page
******************************************************************************/
var oss_LineBar_CpuMemoryUsage_Data_Api_Url = "get_stats_for_server/";
var oss_Area_ReadWrite_Data_Api_Url = "get_fs_stats_for_targets/";
/******************************************************************************
 * Function for cpu and memory usage - Line + Column Chart
 * Param - File System name, start date, end date, datafunction (average/min/max),fetchematrics, isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
oss_LineBar_CpuMemoryUsage_Data = function(hostId, sDate, endDate, dataFunction, fetchMetrics, isZoom)
{
  var count = 0;
  var cpuUserData = [], cpuSystemData = [], cpuIowaitData = [], categories = [], memoryData = [];
  var custom_chart = chartConfig_LineBar_CPUMemoryUsage;
  custom_chart.series = [
    {
      type: 'line',
      data: [],
      name: 'user'
    },
    {
      type: 'line',
      data: [],
      name: 'system'
    },
    {
      type: 'line',
      data: [],
      name: 'iowait'
    },
    {
      type: 'line',
      data: [],
      name: 'mem'
    }
  ];
  obj_oss_LineBar_CpuMemoryUsage_Data = JSON.parse(JSON.stringify(custom_chart));
  
  var api_params = {
    datafunction: dataFunction, fetchmetrics: fetchMetrics, starttime: sDate, host_id: hostId, endtime: endDate
  };
  
  invoke_api_call(api_post, oss_LineBar_CpuMemoryUsage_Data_Api_Url, api_params,
    success_callback = function(data)
    {
      var hostName='';
      var response = data.response;
      $.each(response, function(resKey, resValue) 
      {
        if(resValue.host != undefined)
        {
          if (resValue.cpu_total != undefined && resValue.mem_MemTotal != undefined)
          {
            ts = resValue.timestamp * 1000
            var pct_user = ((100 * resValue.cpu_user + (resValue.cpu_total / 2)) / resValue.cpu_total);
            cpuUserData.push([ts,(pct_user)]);
            var pct_system = ((100 * resValue.cpu_system + (resValue.cpu_total / 2)) / resValue.cpu_total);
            cpuSystemData.push([ts,(pct_system)]);
            var pct_iowait = ((100 * resValue.cpu_iowait + (resValue.cpu_total / 2)) / resValue.cpu_total);
            cpuIowaitData.push([ts,(pct_iowait)]);

            var used_mem = resValue.mem_MemTotal - resValue.mem_MemFree
            var pct_mem = 100 * (used_mem / resValue.mem_MemTotal)
            memoryData.push([ts,(pct_mem)]);
           }
        }
      });

      obj_oss_LineBar_CpuMemoryUsage_Data.chart.renderTo = "oss_avgReadDiv";
      obj_oss_LineBar_CpuMemoryUsage_Data.chart.width='500';
      if(isZoom == 'true')
      {
        renderZoomDialog(obj_oss_LineBar_CpuMemoryUsage_Data);
      }
  
      obj_oss_LineBar_CpuMemoryUsage_Data.series[0].data = cpuUserData;
      obj_oss_LineBar_CpuMemoryUsage_Data.series[1].data = cpuSystemData;
      obj_oss_LineBar_CpuMemoryUsage_Data.series[2].data = cpuIowaitData;
      obj_oss_LineBar_CpuMemoryUsage_Data.series[3].data = memoryData;

      chart = new Highcharts.Chart(obj_oss_LineBar_CpuMemoryUsage_Data);
    },
    error_callback = function(data){
    });
}
/*****************************************************************************
 * Function for disk read and write - Area Chart
 * Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics, isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
oss_Area_ReadWrite_Data = function(fsId, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
{
  obj_oss_Area_ReadWrite_Data = JSON.parse(JSON.stringify(chartConfig_Area_ReadWrite));
  var values = new Object();
  var stats = readWriteFetchMatric;
  $.each(stats, function(i, stat_name)
  {
    values[stat_name] = [];
  });
  
  var api_params = {
    targetkind: targetKind, datafunction: dataFunction, fetchmetrics: stats.join(" "),
    starttime: startTime, filesystem_id: fsId, endtime: endTime
  };
  
  invoke_api_call(api_post, oss_Area_ReadWrite_Data_Api_Url, api_params,
    success_callback = function(data)
    {
      var hostName='';
      var response = data.response;
      $.each(response, function(resKey, resValue)
      {
        if(resValue.filesystem != undefined)
        {
          if (resValue.stats_read_bytes != undefined || resValue.stats_write_bytes != undefined)
          { 
            ts = resValue.timestamp * 1000;
            $.each(stats, function(i, stat_name) 
            {
              if(resValue[stat_name] != null || resValue[stat_name] != undefined) 
              {
                if (i <= 0)
                { 
                  values[stat_name].push([ts, resValue[stat_name]]);
                } 
                else
                {
                  values[stat_name].push([ts, (0 - resValue[stat_name])]);    
                }
              }
            });
          }
        }
      });

      obj_oss_Area_ReadWrite_Data.chart.renderTo = "oss_avgWriteDiv";
      obj_oss_Area_ReadWrite_Data.chart.width='500';
      $.each(stats, function(i, stat_name) 
      {
        obj_oss_Area_ReadWrite_Data.series[i].data = values[stat_name];
      });
      if(isZoom == 'true')
      {
        renderZoomDialog(obj_oss_Area_ReadWrite_Data);
      }
      chart = new Highcharts.Chart(obj_oss_Area_ReadWrite_Data);
  },
  error_callback = function(data){
  });
}
/*****************************************************************************
 * Function to load OSS usage summary information
 * Param - File System Id
 * Return - Returns the summary information of the selected file system
*****************************************************************************/
loadOSSUsageSummary = function (fsId)
{
  $('#ossSummaryTbl').html("<tr><td width='100%' align='center' height='180px'><img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' /></td></tr>");
  var innerContent = "";

  var api_params = {filesystem_id: fsId};

  invoke_api_call(api_post, "getfilesystem/", api_params, 
    success_callback = function(data)
    {
      var response = data.response;
      $.each(response, function(resKey, resValue) 
      {
        innerContent = innerContent + 
        "<tr><td class='greybgcol'>MGS :</td>" +
        "<td class='tblContent greybgcol'>"+resValue.mgs_hostname+"</td>" +
        "<td>&nbsp;</td><td>&nbsp;</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>MDS :</td>" +
        "<td class='tblContent greybgcol'>"+resValue.mds_hostname+"</td>" +
        "<td class='greybgcol'>Failover:</td>" +
        "<td class='tblContent greybgcol'>NA</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>File System :</td>" +
        "<td class='tblContent greybgcol'>"+resValue.fsname+"</td>" +
        "<td>&nbsp;</td><td>&nbsp;</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Total Capacity: </td>" +
        "<td class='tblContent greybgcol'>"+resValue.bytes_total+" </td>" +
        "<td class='greybgcol'>Total Free:</td>" +
        "<td class='tblContent greybgcol'>"+resValue.bytes_free+"</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Files Total: </td>" +
        "<td class='tblContent greybgcol'>"+resValue.inodes_total+" </td>" +
        "<td class='greybgcol'>Files Free:</td>" +
        "<td class='tblContent greybgcol'>"+resValue.inodes_free+"</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Standby OSS :</td>" +
        "<td class='tblContent greybgcol'>--</td>" +
        "<td>&nbsp;</td>" +
        "<td>&nbsp;</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Total OSTs:</td>" +
        "<td class='tblContent greybgcol'>"+resValue.noofost+" </td>" +
        "<td>&nbsp;</td>" +
        "<td>&nbsp;</td>" +
        "</tr>"+
        "<tr><td class='greybgcol'>Status:</td>";

        if(resValue.status == "OK" || resValue.status == "STARTED")
        {
          innerContent = innerContent + "<td><div class='tblContent txtleft status_ok'>"+resValue.status+"<div></td><td>&nbsp;</td><td>&nbsp;</td></tr>";
        }
        else if(resValue.status == "WARNING" || resValue.status == "RECOVERY")
        {
          innerContent = innerContent + "<td><div class='tblContent txtleft status_warning'>"+resValue.status+"</div></td><td>&nbsp;</td><td>&nbsp;</td></tr>";
        }
        else if(resValue.status == "STOPPED")
        {
          innerContent = innerContent + "<td><div class='tblContent txtleft status_stopped'>"+resValue.status+"</div></td><td>&nbsp;</td><td>&nbsp;</td></tr>";
        }
      });

      $('#ossSummaryTbl').html(innerContent);
    },
    error_callback = function(data){
    });
}
/*****************************************************************************
 * Function to initialize polling of graphs on the oss dashboard page
*****************************************************************************/
initOSSPolling = function()
{
  ossPollingInterval = self.setInterval(function()
  {
    loadServerGraphs();
  }, 10000);
}
/*****************************************************************************
 * Function to load graphs on the oss dashboard page
*****************************************************************************/
loadServerGraphs = function()
{
  oss_LineBar_CpuMemoryUsage_Data($('#ls_ossId').val(), startTime, endTime, "Average", cpuMemoryFetchMatric, "false");
  oss_Area_ReadWrite_Data($('#ls_fsId').val(), startTime, endTime, "Average", "OST", readWriteFetchMatric, "false");
}
/******************************************************************************
 * Function to show OST dashboard content
******************************************************************************/
function showOSSDashboard()
{
  loadOSSContent($('#ls_fsId').val(), $('#ls_fsName').val(), $('#ls_ossId').val(), $('#ls_ossName').val());
}
/*********************************************************************************************/
