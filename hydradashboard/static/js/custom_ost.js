/**************************************************************************
 * File Name - custome_ost.js
 * Description - Contains function to plot pie, line and bar charts on OST Screen
 * ---------------------Chart Configurations function-----------------------
 * 1) ChartConfig_OST_Space - Pie chart configuration for space usage.
 * ---------------------Data Loaders function-------------------------------
 * 1) ost_Pie_Space_Data(targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
 * 2) ost_Pie_Inode_Data(targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
 * 3) ost_Area_ReadWrite_Data(targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
******************************************************************************
 * API URL's for all the graphs on OST dashboard page
******************************************************************************/
var ost_Pie_Space_Data_Api_Url = "/api/get_stats_for_targets/";
var ost_Pie_Inode_Data_Api_Url = "/api/get_stats_for_targets/";
var ost_Area_ReadWrite_Data_Api_Url = "/api/get_stats_for_targets/";
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
       return '<b>'+ this.point.name +'</b>: '+ this.y +' %';
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
 * Param - Target name, start date, end date, datafunction (average/min/max), targetKind, fetchematrics, isZoom
 * Return - Returns the graph plotted in container
/*****************************************************************************/
ost_Pie_Space_Data = function(targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
{
  var free=0,used=0;
  var freeData = [],usedData = [];
  obj_ost_pie_space = JSON.parse(JSON.stringify(ChartConfig_OST_Space));
  obj_ost_pie_space.title.text= targetName + " Space Usage";
  obj_ost_pie_space.chart.renderTo = "ost_container2";

  $.post(ost_Pie_Space_Data_Api_Url,
  { 
    targetkind: targetKind, datafunction: dataFunction, fetchmetrics: fetchMetrics, 
    starttime: "", target: targetName, endtime: ""
  })
  .success(function(data, textStatus, jqXHR) 
  {   
    if(data.success)
    {
      var response = data.response;
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
    }
  })
  .error(function(event) 
  {
    // Display of appropriate error message
  })
  .complete(function(event) 
  {
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
    chart = new Highcharts.Chart(obj_ost_pie_space);
  });
} 
/*****************************************************************************
 * Function for free inodes - Pie Chart
 * Param - Target name, start date, end date, datafunction (average/min/max), targetKind, fetchematrics, isZoom
 * Return - Returns the graph plotted in container
/*****************************************************************************/
ost_Pie_Inode_Data = function(targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom) //250
{
  var free=0,used=0;
  var freeFilesData = [],totalFilesData = [];
  obj_ost_pie_inode = JSON.parse(JSON.stringify(ChartConfig_OST_Space));
  obj_ost_pie_inode.title.text= targetName + " - Files vs Free Inodes";
  obj_ost_pie_inode.chart.renderTo = "ost_container3";    
  $.post(ost_Pie_Inode_Data_Api_Url,
  {
    targetkind: targetKind, datafunction: dataFunction, fetchmetrics: fetchMetrics, 
    starttime: "", target: targetName, endtime: ""
  })
  .success(function(data, textStatus, jqXHR) 
  {   
    if(data.success)
    {
      var response = data.response;
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
    }
  })
  .error(function(event) 
  {
    // Display of appropriate error message
  })
  .complete(function(event) 
  {
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
      chart = new Highcharts.Chart(obj_ost_pie_inode);
  });
}

/*****************************************************************************
 * Function for disk read and write - Area Chart
 * Param - Target name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics, isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
ost_Area_ReadWrite_Data = function(targetName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
{
  obj_oss_Area_ReadWrite_Data = JSON.parse(JSON.stringify(chartConfig_Area_ReadWrite));
  var values = new Object();
  var stats = readWriteFetchMatric;
  $.each(stats, function(i, stat_name){
    values[stat_name] = [];
  });
  $.post(ost_Area_ReadWrite_Data_Api_Url,
  {
    targetkind: targetKind, datafunction: dataFunction, fetchmetrics: stats.join(" "),
    starttime: startTime, target: targetName, endtime: endTime
  })
  .success(function(data, textStatus, jqXHR) 
  {
    var hostName='';
    var avgMemoryApiResponse = data;
    if(avgMemoryApiResponse.success)
    {
      var response = avgMemoryApiResponse.response;
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
    }
  })
  .error(function(event) 
  {
    // Display of appropriate error message
  })
  .complete(function(event)
  {
    obj_oss_Area_ReadWrite_Data.chart.renderTo = "ost_avgReadDiv";
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
loadOSTSummary = function (fsName)
{
  var innerContent = "";
  $('#ostSummaryTbl').html("<tr><td width='100%' align='center' height='180px'>" +
      "<img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' /></td></tr>");
  $.post("/api/getfilesystem/",{filesystem: fsName})
  .success(function(data, textStatus, jqXHR) 
  {
    if(data.success)
    {
      var response = data.response;
      $.each(response, function(resKey, resValue) 
      {
        innerContent = innerContent + 
        "<tr>" +
        "<td class='greybgcol'>MGS :</td><td class='tblContent greybgcol'>"+resValue.mgs_hostname+"</td><td>&nbsp;</td><td>&nbsp;</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>MDS :</td>" +
        "<td class='tblContent greybgcol'>"+resValue.mds_hostname+"</td>" +
        "<td class='greybgcol'>Failover :</td><td class='tblContent greybgcol'>NA</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>File System :</td>" +
        "<td class='tblContent greybgcol'>"+resValue.fsname+"</td>" +
        "<td>&nbsp;</td>" +
        "<td>&nbsp;</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Total Capacity: </td>" +
        "<td class='tblContent greybgcol'>"+resValue.kbytesused+" </td>" +
        "<td class='greybgcol'>Total Free:</td>" +
        "<td class='tblContent greybgcol'>"+resValue.kbytesfree+"</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Files Total: </td>" +
        "<td class='tblContent greybgcol'>"+resValue.filestotal+" </td>" +
        "<td class='greybgcol'>Files Free:</td>" +
        "<td class='tblContent greybgcol'>"+resValue.filesfree+"</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Standby OST :</td>" +
        "<td class='tblContent greybgcol'>--</td>" +
        "<td>&nbsp;</td>" +
        "<td>&nbsp;</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Total OSTs:</td>" +
        "<td class='tblContent greybgcol'>"+resValue.noofost+" </td>" +
        "<td>&nbsp;</td><td>&nbsp;</td>" +
        "</tr>"+
        "<tr>" +
        "<td class='greybgcol'>Status:</td>";

        if(resValue.status == "OK" || resValue.status == "STARTED")
        {
          innerContent = innerContent +"<td><div class='tblContent txtleft status_ok'>"+resValue.mdtstatus+"</div></td><td>&nbsp;</td><td>&nbsp;</td></tr>";
        }
        else if(resValue.status == "WARNING" || resValue.status == "RECOVERY")
        {
          innerContent = innerContent +"<td><div class='tblContent txtleft status_warning'>"+resValue.mdtstatus+"</div></td><td>&nbsp;</td><td>&nbsp;</td></tr>";
        }
        else if(resValue.status == "STOPPED")
        {
          innerContent = innerContent +"<td><div class='tblContent txtleft status_stopped'>"+resValue.mdtstatus+"</div></td><td>&nbsp;</td><td>&nbsp;</td></tr>";
        }
      });
    }
  })
  .error(function(event) 
  {

  })
  .complete(function(event)
  {
    $('#ostSummaryTbl').html(innerContent);
  });
}
/*****************************************************************************
 * Function to initialize polling of graphs on the ost dashboard page
*****************************************************************************/
initOSTPolling = function()
{
  ost_Pie_Space_Data($('#ls_ost').val(), "", "", "Average", "OST", spaceUsageFetchMatric, "false");
  ost_Pie_Inode_Data($('#ls_ost').val(), "", "", "Average", "OST", spaceUsageFetchMatric, "false");
  ost_Area_ReadWrite_Data($('#ls_ost').val(), startTime, endTime, "Average", "OST", readWriteFetchMatric, "false");
}
/*********************************************************************************************/
