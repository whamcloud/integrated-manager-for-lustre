/**************************************************************************
 * File Name - custome_ost.js
 * Description - Contains function to plot pie, line and bar charts on OST Screen
 * ---------------------Chart Configurations function-----------------------
 * 1) ChartConfig_OST_Space - Pie chart configuration for space usage.
 * ---------------------Data Loaders function-------------------------------
 * 1) ost_Pie_Space_Data(targetId, targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
 * 2) ost_Pie_Inode_Data(targetId, targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
 * 3) ost_Area_ReadWrite_Data(targetId, targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
******************************************************************************
 * API URL's for all the graphs on OST dashboard page
******************************************************************************/
var ost_Pie_Space_Data_Api_Url = "get_stats_for_targets/";
var ost_Pie_Inode_Data_Api_Url = "get_stats_for_targets/";
var ost_Area_ReadWrite_Data_Api_Url = "get_stats_for_targets/";
var mdt_ops_fetch_metrics= ["stats_close", "stats_getattr", "stats_getxattr", "stats_link",
                        "stats_mkdir", "stats_mknod", "stats_open", "stats_rename",
                        "stats_rmdir", "stats_setattr", "stats_statfs", "stats_unlink"];
/******************************************************************************
* OST specific functions
******************************************************************************/
show_hide_targetSpaceUsageContainer = function(displayValue)
{
  $("#target_space_usage_container").css("display", displayValue);
}
show_hide_targetFilesUsageContainer = function(displayValue)
{
  $("#target_inodes_container").css("display", displayValue);
}
show_hide_targetReadWriteContainer = function(displayValue)
{
  $("#target_read_write_container_div").css("display" ,displayValue);
}
show_hide_targetMgtOpsContainer = function(displayValue)
{
  $("#target_mgt_ops_container_div").css("display" ,displayValue);
}

/*****************************************************************************
 * Configuration object for space usage - Pie Chart
******************************************************************************/
var ChartConfig_OST_Space = 
{
  chart:
  {
    renderTo: '',
    marginLeft: '50',
    width: '250',
    height: '200',
    style:{ width:'100%',  height:'200px' },
    backgroundColor: '#f9f9ff',
  },
  colors: [
    '#A6C56D', 
    '#C76560', 
    '#A6C56D', 
    '#C76560', 
    '#6087B9', 
    '#DB843D', 
    '#92A8CD', 
    '#A47D7C', 
    '#B5CA92'
  ],
  title:{ text: '', style: { fontSize: '12px' }, },
  zoomType: 'xy',
  xAxis:{ categories: [], text: '' },
  yAxis:{ text: '', plotLines: [ { value: 0, width: 1, color: '#808080' } ] },
  credits:{ enabled:false },
  tooltip:
  {
    formatter: function() 
    {
       return '<b>'+ this.point.name +'</b>: '+ this.percentage +' %';
    }
  },
  plotOptions:
  {
    pie:
    { 
      allowPointSelect: true, cursor: 'pointer', showInLegend: true, size: '100%', 
      dataLabels:
      {
        enabled: false,color: '#000000',connectorColor: '#000000'
      }
    }
  },
  series: []
};  
/*****************************************************************************
 * Function for space usage data - Pie Chart
 * Param - Target Id, Target name, start date, end date, datafunction (average/min/max), targetKind, fetchematrics, isZoom
 * Return - Returns the graph plotted in container
/*****************************************************************************/
ost_Pie_Space_Data = function(targetId, targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
{
  var free=0,used=0;
  var freeData = [],usedData = [];
  obj_ost_pie_space = JSON.parse(JSON.stringify(ChartConfig_OST_Space));
  obj_ost_pie_space.title.text= targetName + " Space Usage";
  obj_ost_pie_space.chart.renderTo = "target_space_usage_container";

  var api_params = { 
      targetkind: targetKind, datafunction: dataFunction, fetchmetrics: fetchMetrics, 
      starttime: "", target_id: targetId, endtime: ""
  };
  
  Api.post(ost_Pie_Space_Data_Api_Url, api_params,
    success_callback = function(data)
    {
      var response = data;
      var totalDiskSpace=0,totalFreeSpace=0;
      $.each(response, function(resKey, resValue) 
      {
        if(resValue.target != undefined)
        {
          totalFreeSpace = resValue.kbytesfree/1024;
          totalDiskSpace = resValue.kbytestotal/1024;
          free = Math.round(((totalFreeSpace/1024)/(totalDiskSpace/1024))*100);
          used = Math.round(100 - free);
  
          freeData.push(free);
          usedData.push(used);
        }
      });
 
      obj_ost_pie_space.series = 
      [{
        type: 'pie',
        name: 'Browser share',
        data: 
          [
               ['Free',    free],
               ['Used',    used]
          ]
      }];
      obj_ost_pie_space.tooltip = 
      {
        formatter: function() 
        {
           return '<b>'+ this.point.name +'</b>: '+ this.percentage +' %';
        }
      };
      chart = new Highcharts.Chart(obj_ost_pie_space);
    });
} 
/*****************************************************************************
 * Function for free inodes - Pie Chart
 * Param - Target Id, Target name, start date, end date, datafunction (average/min/max), targetKind, fetchematrics, isZoom
 * Return - Returns the graph plotted in container
/*****************************************************************************/
ost_Pie_Inode_Data = function(targetId, targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom) //250
{
  var free=0,used=0;
  var freeFilesData = [],totalFilesData = [];
  obj_ost_pie_inode = JSON.parse(JSON.stringify(ChartConfig_OST_Space));
  obj_ost_pie_inode.title.text= targetName + " - Files vs Free Inodes";
  obj_ost_pie_inode.chart.renderTo = "target_inodes_container";
  
  var api_params = {
      targetkind: targetKind, datafunction: dataFunction, fetchmetrics: fetchMetrics, 
      starttime: "", target_id: targetId, endtime: ""
  };
  
  Api.post(ost_Pie_Inode_Data_Api_Url, api_params,
    success_callback = function(data)
    {
      var response = data;
      var totalFiles=0,totalFreeFiles=0;
      $.each(response, function(resKey, resValue) 
      {
        if(resValue.target != undefined)
        {
          totalFiles = resValue.filesfree/1024;
          totalFreeFiles = resValue.filestotal/1024;
          free = Math.round(((totalFiles/1024)/(totalFreeFiles/1024))*100);
          used = Math.round(100 - free);

          freeFilesData.push(free);
          totalFilesData.push(used);
        }   
      });

      obj_ost_pie_inode.series = 
      [{
        type: 'pie',
        name: 'Browser share',
        data: 
          [
            ['Free',    free],
            ['Used',    used]
          ]
      }];
      obj_ost_pie_inode.tooltip = 
      {
        formatter: function() 
        {
           return '<b>'+ this.point.name +'</b>: '+ this.percentage +' %';
        }
      };
      chart = new Highcharts.Chart(obj_ost_pie_inode);
    });
}
/*****************************************************************************
 * Function for mgt ops - Area Chart
 * Param - Target Id, isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
ost_Area_mgtOps_Data = function(targetId, isZoom)
{
  var closeData = [], getattrData = [], getxattrData = [], linkData = [], mkdirData = [], mknodData = [], openData = [], renameData = [], rmdirData = [], setattrData = [], statfsData = [], unlinkData = [];
  obj_db_Area_mdOps_Data = JSON.parse(JSON.stringify(chartConfig_Area_mdOps));

  var values = new Object();
  var stats = mdOpsFetchmatric;
  $.each(stats, function(i, stat_name)
  {
    values[stat_name] = [];
  });
  
  var api_params = {
      targetkind: "MDT", datafunction: "Average", fetchmetrics: stats.join(" "),
      starttime: startTime,  target_id: targetId, endtime: endTime
  };
  
  Api.post(ost_Area_ReadWrite_Data_Api_Url, api_params,
    success_callback = function(data)
    {
      var targetName='';
      var response = data;
      $.each(response, function(resKey, resValue)
      {
        if(resValue.filesystem != undefined)
        {
          ts = resValue.timestamp * 1000;
          $.each(stats, function(i, stat_name)
          {
            if (resValue[stat_name] != null || resValue[stat_name] != undefined)
            {
              values[stat_name].push([ts, resValue[stat_name]])
            }
          });
          }
      });

      obj_db_Area_mdOps_Data.chart.renderTo = "target_mgt_ops_container";
      obj_db_Area_mdOps_Data.chart.width = "480";
      if(isZoom == 'true')
      {
        renderZoomDialog(obj_db_Area_mdOps_Data);
      }
      $.each(stats, function(i, stat_name)
      {
        obj_db_Area_mdOps_Data.series[i].data = values[stat_name];
      });
      chart = new Highcharts.Chart(obj_db_Area_mdOps_Data);
    });
}

/*****************************************************************************
 * Function for disk read and write - Area Chart
 * Param - Target Id, Target name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics, isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
ost_Area_ReadWrite_Data = function(targetId, targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
{
  obj_oss_Area_ReadWrite_Data = JSON.parse(JSON.stringify(chartConfig_Area_ReadWrite));
  var values = new Object();
  var stats = readWriteFetchMatric;
  $.each(stats, function(i, stat_name){
    values[stat_name] = [];
  });
  
  var api_params = {
      targetkind: targetKind, datafunction: dataFunction, fetchmetrics: stats.join(" "),
      starttime: startTime, target_id: targetId, endtime: endTime
  };
  
  Api.post(ost_Area_ReadWrite_Data_Api_Url, api_params,
    success_callback = function(data)
    {
      var hostName='';
      var response = data;
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

      obj_oss_Area_ReadWrite_Data.chart.renderTo = "target_read_write_container";
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
    });
}
/*****************************************************************************
 * Function to load OST usage summary information
 * Param - File System name
 * Return - Returns the summary information of the selected file system
*****************************************************************************/
loadOSTSummary = function (fsId)
{
  //console.log("loadOSTSummary");
  var innerContent = "";
  $('#ostSummaryTbl').html("<tr><td width='100%' align='center' height='180px'>" +
      "<img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' /></td></tr>");

  Api.get("filesystem/" + fsId + "/", {}, 
    success_callback = function(filesystem)
    {
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
      "</tr>"

      $('#ostSummaryTbl').html(innerContent);
    });
}
/*****************************************************************************
 * Function to initialize polling of graphs on the ost dashboard page
*****************************************************************************/
initOSTPolling = function()
{
  ossPollingInterval = self.setInterval(function()
  {
    loadTargetGraphs();
  }, 10000);
}
/*****************************************************************************
 * Function to load graphs on the ost dashboard page
*****************************************************************************/
loadTargetGraphs = function()
{
  var ostKind = $("#ls_ostKind").val();
  if(ostKind == 'OST')
  {
    ost_Pie_Space_Data($('#ls_ostId').val(), $('#ls_ostName').val(), "", "", "Average", $('#ls_ostKind').val(), spaceUsageFetchMatric, "false");
    ost_Pie_Inode_Data($('#ls_ostId').val(), $('#ls_ostName').val(), "", "", "Average", $('#ls_ostKind').val(), spaceUsageFetchMatric, "false");
    ost_Area_ReadWrite_Data($('#ls_ostId').val(), $('#ls_ostName').val(), startTime, endTime, "Average", $('#ls_ostKind').val(), readWriteFetchMatric, "false");
    show_hide_targetSpaceUsageContainer("block");
    show_hide_targetFilesUsageContainer("block");
    show_hide_targetReadWriteContainer("block");
    show_hide_targetMgtOpsContainer("none");
  }
  else if (ostKind == 'MDT')
  {
    ost_Area_mgtOps_Data($('#ls_ostId').val(), "false");
    show_hide_targetReadWriteContainer("none")
    show_hide_targetSpaceUsageContainer("none"); 
    show_hide_targetFilesUsageContainer("none");
    show_hide_targetMgtOpsContainer("block");
  }
  else
  {
    show_hide_targetSpaceUsageContainer("none");
    show_hide_targetFilesUsageContainer("none");
    show_hide_targetReadWriteContainer("none");
    show_hide_targetMgtOpsContainer("none");
  }
}
/*****************************************************************************/
