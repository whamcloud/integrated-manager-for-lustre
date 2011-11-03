/*******************************************************************************
 * File name: custom_dashboard.js
 * Description: Plots all the graphs for dashboard landing page.
 * ------------------Configuration functions--------------------------------------
 * 1) chartConfig_Bar_SpaceUsage    -  Bar chart configuration for space and inodes graph
 * 2) chartConfig_Line_clientConnected  -  Line chart configuration for number of clients connected
 * 3) chartConfig_LineBar_CPUMemoryUsage  -  Column chart for cpu usage and line chart for memory usage
 * 4) chartConfig_Area_ReadWrite    -  Area graph for disk reads and writes
 * 5) chartConfig_Area_mdOps      -  Area graph for mdOP/s
 * 6) chartConfig_HeatMap
 * ------------------ Data Loader functions--------------------------------------
 * 1) db_Bar_SpaceUsage_Data(isZoom)
 * 2) db_Line_connectedClients_Data(isZoom)
 * 3) db_LineBar_CpuMemoryUsage_Data(isZoom)
 * 4) db_Area_ReadWrite_Data(isZoom)
 * 5) db_Area_mdOps_Data(isZoom)
 * 6) db_HeatMap_Data(fetchmetrics, isZoom)
 * 7) db_HeatMap_CPUData(fetchmetrics, isZoom)
 * 8) renderZoomDialog(configObject)
 * 9) setZoomDialogTitle(titleName)
 * 10) initDashboardPolling 
 * 11) clearAllIntervals
 * 12) showFSDashboard
 * 13) showOSSDashboard 
/*******************************************************************************
 * Fetch Metrics for all the graphs
******************************************************************************/
var spaceUsageFetchMatric = "kbytestotal kbytesfree filestotal filesfree";
var clientsConnectedFetchMatric = "num_exports";
var cpuMemoryFetchMatric = "cpu_usage cpu_total mem_MemFree mem_MemTotal";
var readWriteFetchMatric = ["stats_read_bytes", "stats_write_bytes"];
var mdOpsFetchmatric = ["stats_close", "stats_getattr", "stats_getxattr", "stats_link", 
                        "stats_mkdir", "stats_mknod", "stats_open", "stats_rename", 
                        "stats_rmdir", "stats_setattr", "stats_statfs", "stats_unlink"]
var ioOpsFetchmatric = ["stats_connect","stats_create","stats_destroy","stats_disconnect",
                        "stats_get_info","stats_get_page","stats_llog_init","stats_ping",
                        "stats_punch","stats_preprw","stats_set_info_async","stats_statfs","stats_sync"];
/*******************************************************************************
 * Global variable declaratiom
******************************************************************************/
var dashboardPollingInterval,fsPollingInterval;
var startTime = "5";
var endTime = "";
var isPollingFlag=false;
/*******************************************************************************
 * API URL's for all the graphs on landing page
******************************************************************************/
var db_Bar_SpaceUsage_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var db_Line_connectedClients_Data_Api_Url = "/api/get_fs_stats_for_client/";
var db_LineBar_CpuMemoryUsage_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var db_Area_ReadWrite_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var db_Area_mdOps_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var db_HeatMap_Data_Api_Url = "/api/get_fs_ost_heatmap_fake/";
/*****************************************************************************
 * Configuration object for space usage - Stacked Bar Chart
******************************************************************************/
var chartConfig_Bar_SpaceUsage = 
{    
  chart:
  {
    renderTo: '',
    marginLeft: '50',
    width: '300',
    height: '200',
    style:{ width:'100%',  height:'200'},
    marginBottom: 35,
    defaultSeriesType: 'column',
    backgroundColor: '#f9f9ff',
  },
  colors: 
  [
    '#A6C56D', 
    '#C76560', 
    '#A6C56D', 
    '#C76560', 
    '#3D96AE', 
    '#DB843D', 
    '#92A8CD', 
    '#A47D7C', 
    '#B5CA92'
  ],
  plotOptions: {
     column: {
      stacking: 'normal',
     }
  },
  legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
  title:{text:'', style: { fontSize: '12px' } },
  zoomType: 'xy',
  xAxis:{ categories: ['Usage'], text: '', labels : { rotation: 310, style:{fontSize:'8px', fontWeight:'regular'} } },
  yAxis:{max:100, min:0, startOnTick:false, title:{text:'Percentage'}, plotLines: [ { value: 0,width: 1, color: '#808080' } ] },
  credits:{ enabled:false },
  tooltip:
  {
    formatter: function() 
    {
      var tooltiptext;
      if (this.point.name) 
      { 
        tooltiptext = ''+
        this.point.name +': '+ this.y +'';
      } 
      else 
      {
        tooltiptext = ''+
        this.x  +': '+ this.y;
      }
      return tooltiptext;
    }  
  },
  labels:{ items:[{html: '',style:{left: '40px',top: '8px',color: 'black'}}]},
  series: []
};
/*****************************************************************************
 * Configuration object for client connected - Line Chart
******************************************************************************/
var chartConfig_Line_clientConnected = 
{
  chart: 
  {
    renderTo: 'container3',
    marginLeft: '50',
    width: '300',
    height: '200',
    style:{ width:'100%',  height:'210'},
    marginBottom: 35,
    zoomType: 'xy',
    backgroundColor: '#f9f9ff',
  },
  title: 
  {
    text: 'Connected Clients',
    style: { fontSize: '12px' },
  },
  xAxis: 
  {
    type:'datetime',
  },
  yAxis: 
  {
    min:0, startOnTick:false,
    title: {
      text: 'Clients'
    },
    plotLines: [{
      value: 0,
      width: 1,
      color: '#808080'
    }]
  },
  tooltip: 
  {
    formatter: function() {
      return 'Time: '+this.x +'No. Of Exports: '+ this.y;
    }
  },
  legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
  credits:{ enabled:false },
  series: 
  [{
      name: '',
      data: []
  }],
  plotOptions: {
    series:{marker: {enabled: false}}
  },
};
/*****************************************************************************
 * Configuration object for cpu and memory usage - Line + Bar Chart
******************************************************************************/
var chartConfig_LineBar_CPUMemoryUsage = 
{
  chart: 
  {
    renderTo: 'avgCPUDiv',
    marginLeft: '50',
    width: '300',
    height: '200',
    style:{ width:'100%',  height:'210'},
    marginBottom: 35,
    zoomType: 'xy',
    backgroundColor: '#f9f9ff',
  },
  title: 
  {
    text: 'Server CPU and Memory',
    style: { fontSize: '12px' },
  },
  xAxis:
  {
    type:'datetime',
  },
  yAxis: 
  [
    {
     title: {
       text: 'KB'
     },
     opposite: true,
    },
    {
      title: {
        text: 'Percentage'
      },
      max:100, min:0, startOnTick:false,  tickInterval: 20
    }
  ],
  legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
  credits:{ enabled:false },
  plotOptions:
  {
    series:{marker: {enabled: false}},
    column:{
    pointPadding: 0.0,
    shadow: false,
    groupPadding: 0.0,
    borderWidth: 0.0
    }
  },
  series: 
    [
      {
        type: 'column',
        data: [],
        name: 'CPU Usage',
        yAxis: 1
      },
      {
        type: 'line',
        data: [],
        name: 'Memory',
      }
    ]
};
/*****************************************************************************
 * Configuration object for read/write - Area Chart
******************************************************************************/
var chartConfig_Area_ReadWrite = 
{
  chart: 
  {
    renderTo: 'avgMemoryDiv',
    defaultSeriesType: 'area',
    marginLeft: '50',
    width: '300',
    height: '200',
    style:{ width:'100%',  height:'210'},
    marginRight: 0,
    marginBottom: 35,
    backgroundColor: '#f9f9ff',
    zoomType: 'xy'
  },
  colors: 
  [
    '#6285AE', 
    '#AE3333', 
    '#A6C56D', 
    '#C76560', 
    '#3D96AE', 
    '#DB843D', 
    '#92A8CD', 
    '#A47D7C', 
    '#B5CA92'
   ],
   title: 
   {
     text: 'Read vs Writes',
     style: { fontSize: '12px' },
   },
   xAxis:
   {
      type:'datetime',  
   },
   yAxis: 
   {
     title: {text: 'KB'}
   },
   tooltip: 
   {
       formatter: function() 
       {
         return ''+this.series.name +': '+ this.y +'';
       }
   },
   legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
   credits:{ enabled:false },
   plotOptions:
   { 
     series:{marker: {enabled: false}} 
   },
   credits: { enabled: false },
   series: [{ name: 'Read', data: []}, { name: 'Write',data: []}]
}
/*****************************************************************************
 * Configuration object for mdOps - Area Chart
******************************************************************************/
var chartConfig_Area_mdOps  = 
{
  chart:
  {
    defaultSeriesType: 'area',
    marginLeft: '50',
    height: '200',
    width: '300',
    style:{ width:'100%',  height:'210'},
    marginRight: 0,
    marginBottom: 35,
    zoomType: 'xy',
    backgroundColor: '#f9f9ff'
  },
  colors: 
  [
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
  title: 
  {
    text: 'Metadata ops',
    style: { fontSize: '12px' },
  },
  xAxis: 
  {
    type: 'datetime'
  },
  yAxis: 
  {
    title:
    {
      text: 'MD op/s'
    },
  },
  tooltip: 
  {
    formatter: function() 
    {
      return ''+ this.x +': '+ Highcharts.numberFormat(this.y, 0, ',') +' ';
    }
  },
  legend:
  {
    enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0
  },
  credits:{ enabled:false },
  plotOptions: 
  {
    series:{marker: {enabled: false}},
    area: 
    {
      stacking: 'normal',
      lineColor: '#666666',
      lineWidth: 1,
      marker: {
        lineWidth: 1,
        lineColor: '#666666'
      }
     }
   },
   series: [{
     name: 'close'
     }, {
       name: 'getattr'
     }, {
       name: 'getxattr'
     }, {
       name: 'link'
     }, {
       name: 'mkdir'
     }, {
       name: 'mknod'
     }, {
       name: 'open'
     }, {
       name: 'rename'
     }, {
       name: 'rmdir'
     }, {
       name: 'setattr'
     }, {
       name: 'statfs'
     }, {
       name: 'unlink'
     }]
}
/*****************************************************************************
 * Configuration object for Heat Map
******************************************************************************/
var chartConfig_HeatMap = 
{
  chart: 
  {
    renderTo: '', 
    defaultSeriesType: 'scatter',
    marginLeft: '50',
    width: '900',
    height: '200',
    style:{ width:'100%',  height:'210'},
    marginRight: 0,
    marginBottom: 35,
    zoomType: 'xy'
  },
  title: 
  {
    text: 'Heat Map',
    style: { fontSize: '12px' }
  },
  xAxis: 
  {
    title: 
    {
      enabled: true,
      text: 'Time'
     },
    type: 'datetime'
   },
   yAxis: 
   {
     title: {
       text: 'Items'
     },
     labels:{enabled:false},
     alternateGridColor: '#FDFFD5',
     tickInterval:1,
     plotBands:[]
   },
   tooltip: 
   {
     formatter: function() {
           return ''+ this.x +' , '+ this.y +' ';
     }
   },
   legend: 
   {
     enabled : false,
     layout: 'vertical',
     align: 'right',
     verticalAlign: 'top',
     x: 0,
     y: 10,
     floating: true,
     borderWidth: 0
   },
   plotOptions: 
   {
     scatter: 
     {
       marker: 
       {
         radius: 5,
         lineColor: 'black',
         lineWidth: 0.5,
         states: 
         {
           hover: {
             enabled: true,
             lineColor: 'rgb(100,100,100)'
          }
         }
       },
       states: 
       {
         hover: {
           marker: {
             enabled: false
          }
         }
       }
     }
   },
   credits:{ enabled:false },
   series : []
};
/*****************************************************************************
 * Configuration object for Iops
******************************************************************************/
var chartConfig_AreaSpline =
{
  chart: 
  {
    renderTo: 'container',
    defaultSeriesType: 'areaspline',
    marginLeft: '50',
    width: '900',
    height: '200',
    style:{ width:'100%',  height:'210'},
    marginRight: 0,
    marginBottom: 35,
    zoomType: 'xy'
  },
  title: 
  {
    text: 'IOPs',
    style: { fontSize: '12px' }
  },
  legend: 
  {
    enabled : false,
    layout: 'vertical',
    align: 'right',
    verticalAlign: 'top',
    x: 0,
    y: 10,
    floating: true,
    borderWidth: 0
  },
  xAxis: 
  {
    type:"datetime"
  },
  yAxis: 
  {
    title: 
    {
      text: 'IO Iops'
    }
  },
  tooltip: 
  {
    formatter: function() {
      return ''+ this.x +': '+ this.y +' units';
    }
  },
  credits: 
  {
    enabled: false
  },
  plotOptions:
  {
    areaspline: 
    {
      fillOpacity: 0.5
    }
  },
  series: [{
    name: 'stats_connect',
    data: []
  }]
  
    /*{
      name: 'stats_connect'
    }, {
      name: 'stats_create'
    }, {
      name: 'stats_destroy'
    }, {
      name: 'stats_disconnect'
    }, {
      name: 'stats_get_info'
    }, {
      name: 'stats_get_page'
    }, {
      name: 'stats_llog_init'
    }, {
      name: 'stats_ping'
    }, {
      name: 'stats_punch'
    }, {
      name: 'stats_preprw'
    }, {
      name: 'stats_set_info_async'
    }, {
      name: 'stats_statfs'
    }, {
      name: 'stats_sync'
    }*/
};
/*****************************************************************************
 * Function for space usage for all file systems  - Stacked Bar Chart
 * Param - isZoom
 * Return - Returns the graph plotted in container
******************************************************************************/
db_Bar_SpaceUsage_Data = function(isZoom)
{
  var free=0,used=0;
  var freeData = [],usedData = [],categories = [],freeFilesData = [],totalFilesData = [];
  $.post(db_Bar_SpaceUsage_Data_Api_Url,
  {
    targetkind: "OST", datafunction: "Average", fetchmetrics: spaceUsageFetchMatric, 
    starttime: "", filesystem_id: "", endtime: ""
  })
  .success(function(data, textStatus, jqXHR) 
  {   
    if(data.success)
    {
      var response = data.response;
      var totalDiskSpace=0,totalFreeSpace=0,totalFiles=0,totalFreeFiles=0;
      $.each(response, function(resKey, resValue) 
      {
        if(resValue.filesystem != undefined)
        {
          totalFreeSpace = resValue.kbytesfree/1024;
          totalDiskSpace = resValue.kbytestotal/1024;
          free = Math.round(((totalFreeSpace/1024)/(totalDiskSpace/1024))*100);
          used = Math.round(100 - free);
          
          freeData.push(free);
          usedData.push(used);
          
          totalFiles = resValue.filesfree/1024;
          totalFreeFiles = resValue.filestotal/1024;
          free = Math.round(((totalFreeSpace/1024)/(totalDiskSpace/1024))*100);
          used = Math.round(100 - free);
          
          freeFilesData.push(free);
          totalFilesData.push(used);
          
          categories.push(resValue.filesystem);
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
    obj_db_Bar_SpaceUsage_Data = JSON.parse(JSON.stringify(chartConfig_Bar_SpaceUsage));
    obj_db_Bar_SpaceUsage_Data.chart.renderTo = "container";
    obj_db_Bar_SpaceUsage_Data.xAxis.categories = categories;
    obj_db_Bar_SpaceUsage_Data.title.text="All File System Space Usage";
    obj_db_Bar_SpaceUsage_Data.series = 
      [
         {data: freeData, stack: 0, name: 'Free Space'}, {data: usedData, stack: 0, name: 'Used Space'},      // first stack
         {data: freeFilesData, stack: 1, name: 'Free Files'}, {data: totalFilesData, stack: 1, name: 'Used Files'}  // second stack
      ]  
    if(isZoom == 'true')
    {
      renderZoomDialog(obj_db_Bar_SpaceUsage_Data);
    }
    chart = new Highcharts.Chart(obj_db_Bar_SpaceUsage_Data);
  });
}
/*****************************************************************************
 * Function for number of clients connected  - Line Chart
 * Param - isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
db_Line_connectedClients_Data = function(isZoom)
{
  obj_db_Line_connectedClients_Data = JSON.parse(JSON.stringify(chartConfig_Line_clientConnected));
  var clientMountData = [];
  var count=0;
  var fileSystemName = "";
  $.post(db_Line_connectedClients_Data_Api_Url,
  {
    fetchmetrics: clientsConnectedFetchMatric, endtime: endTime, datafunction: "Average", 
    starttime: startTime, filesystem_id: ""
  })
  .success(function(data, textStatus, jqXHR) 
  {   
    if(data.success)
    {
      var response = data.response;
      $.each(response, function(resKey, resValue) 
      {
        if(resValue.filesystem != undefined)
        {
          if (fileSystemName != resValue.filesystem && fileSystemName !='')
          {
            obj_db_Line_connectedClients_Data.series[count] =
              {
                name: fileSystemName,
                data: clientMountData
              };
            clientMountData = [];
            count++;
            if (resValue.num_exports != null || resValue.num_exports != undefined)
            {
              ts = resValue.timestamp * 1000
              fileSystemName = resValue.filesystem;
              clientMountData.push([ts,resValue.num_exports]);
            }
          }
          else
          {
            if (resValue.num_exports != null || resValue.num_exports != undefined)
            { 
              ts = resValue.timestamp * 1000
              fileSystemName = resValue.filesystem;
              clientMountData.push([ts,resValue.num_exports]);
            }
          }
        }
      });
      obj_db_Line_connectedClients_Data.series[count] = { name: fileSystemName, data: clientMountData}; 
    }
  })
  .error(function(event) 
  {
    // Display of appropriate error message
  })
  .complete(function(event)
  {
    obj_db_Line_connectedClients_Data.chart.renderTo = "container3";
    if(isZoom == 'true')
    {
      renderZoomDialog(obj_db_Line_connectedClients_Data);
    }
    chart = new Highcharts.Chart(obj_db_Line_connectedClients_Data);
   });
}

/*****************************************************************************
 * Function for cpu and memory usage - Line + Column Chart
 * Param - isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
db_LineBar_CpuMemoryUsage_Data = function(isZoom)
{
  var count = 0;
  var cpuData = [],categories = [], memoryData = [];
  obj_db_LineBar_CpuMemoryUsage_Data = JSON.parse(JSON.stringify(chartConfig_LineBar_CPUMemoryUsage));
  $.post(db_LineBar_CpuMemoryUsage_Data_Api_Url,
  {
    targetkind: 'HOST',fetchmetrics: cpuMemoryFetchMatric, endtime: endTime, datafunction: "Average", 
    starttime: startTime, filesystem_id: ""
  })
  .success(function(data, textStatus, jqXHR) 
  {
    var hostName='';
    var avgCPUApiResponse = data;
    if(avgCPUApiResponse.success)
    {
      var response = avgCPUApiResponse.response;
      $.each(response, function(resKey, resValue) 
      {
          if (resValue.cpu_usage != undefined || resValue.cpu_total != undefined)          
          {
            ts = resValue.timestamp * 1000
            cpuData.push([ts,((resValue.cpu_usage*100)/resValue.cpu_total)]);
            memoryData.push([ts,(resValue.mem_MemTotal - resValue.mem_MemFree)]);
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
    obj_db_LineBar_CpuMemoryUsage_Data.chart.renderTo = "avgCPUDiv";
    if(isZoom == 'true')
    {
      renderZoomDialog(obj_db_LineBar_CpuMemoryUsage_Data);
    } 
    obj_db_LineBar_CpuMemoryUsage_Data.series[0].data = cpuData;
    obj_db_LineBar_CpuMemoryUsage_Data.series[1].data = memoryData;
    if(isZoom == 'true')
    {
       renderZoomDialog(obj_db_LineBar_CpuMemoryUsage_Data);
    }
    chart = new Highcharts.Chart(obj_db_LineBar_CpuMemoryUsage_Data);
  });
}
/*****************************************************************************
 * Function for disk read and write - Area Chart
 * Param - isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
db_Area_ReadWrite_Data = function(isZoom)
{
  obj_db_Area_ReadWrite_Data = JSON.parse(JSON.stringify(chartConfig_Area_ReadWrite));
  var values = new Object();
  var stats = readWriteFetchMatric;
  $.each(stats, function(i, stat_name)
  {
    values[stat_name] = [];
  });
  $.post(db_Area_ReadWrite_Data_Api_Url,
  {
    targetkind: "OST", datafunction: "Average", fetchmetrics: stats.join(" "),
    starttime: startTime, filesystem_id: "", endtime: endTime
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
                  values[stat_name].push([ts, (resValue[stat_name]/1024)]);
                } 
                else
                {
                  values[stat_name].push([ts, (0 - (resValue[stat_name])/1024)]);    
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
    obj_db_Area_ReadWrite_Data.chart.renderTo = "avgMemoryDiv";
    $.each(stats, function(i, stat_name)
    {
      obj_db_Area_ReadWrite_Data.series[i].data = values[stat_name];
    });
    if(isZoom == 'true')
    {
      renderZoomDialog(obj_db_Area_ReadWrite_Data);
    }
    chart = new Highcharts.Chart(obj_db_Area_ReadWrite_Data);
  });
}

/*****************************************************************************
 * Function for mdOps - Area Chart
 * Param - isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
db_Area_mdOps_Data = function(isZoom)
{
  var closeData = [], getattrData = [], getxattrData = [], linkData = [], mkdirData = [], mknodData = [], openData = [], renameData = [], rmdirData = [], setattrData = [], statfsData = [], unlinkData = [];
  obj_db_Area_mdOps_Data = JSON.parse(JSON.stringify(chartConfig_Area_mdOps));

  var values = new Object();
  var stats = mdOpsFetchmatric;
  $.each(stats, function(i, stat_name)
  {
    values[stat_name] = [];
  });
  $.post(db_Area_mdOps_Data_Api_Url,
  {
    targetkind: "MDT", datafunction: "Average", fetchmetrics: stats.join(" "),
    starttime: startTime, filesystem_id: "", endtime: endTime
  })
  .success(function(data, textStatus, jqXHR) 
  {
    var targetName='';
    var avgDiskReadApiResponse = data;
    if(avgDiskReadApiResponse.success)
    {
      var response = avgDiskReadApiResponse.response;
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
    }
  })
  .error(function(event) 
  {
    // Display of appropriate error message
  })
  .complete(function(event)
  {
    obj_db_Area_mdOps_Data.chart.renderTo = "avgReadDiv";
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
 * Function for mdOps - Area Spline Chart
 * Params - fetchmatrics, isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
db_AreaSpline_ioOps_Data = function(isZoom)
{
  obj_db_AreaSpline_ioOps_Data = JSON.parse(JSON.stringify(chartConfig_AreaSpline));

  var values = new Object();
  var stats = ioOpsFetchmatric;
  $.each(stats, function(i, stat_name)
  {
    values[stat_name] = [];
  });
  $.post("/api/get_fs_stats_heatmap/",
  {
    fetchmetrics: stats.join(" "), endtime: endTime, datafunction: "Average", 
    starttime: startTime, filesystem: "", targetkind:"OST"
  })
  .success(function(data, textStatus, jqXHR) 
  {
    var targetName='';
    var count=0;
    var iopsDataResponse = data;
    if(iopsDataResponse.success)
    {
      var response = data.response;
      $.each(response, function(resKey, resValue)
      {
          if (targetName != resValue.targetname && targetName !='')
          {
            $.each(stats, function(i, stat_name)
            {
              obj_db_AreaSpline_ioOps_Data.series[count] = 
              {
                  name: targetName,
                  data: values[stat_name],
              };
              count++;
            });
            $.each(stats, function(i, stat_name)
            {
              values[stat_name] = [];
            });
            

            targetName = resValue.targetname;
            
            if(targetName != undefined)
            {
              ts = resValue.timestamp * 1000;
              $.each(stats, function(i, stat_name) 
              {
                if (resValue[stat_name] != null || resValue[stat_name] != undefined) 
                {
                  values[stat_name].push([ts, resValue[stat_name]]);
                }
              });
            }
          }
          else
          {
            targetName = resValue.targetname;
            
            if(targetName != undefined)
            {
              ts = resValue.timestamp * 1000;
              $.each(stats, function(i, stat_name) 
              {
                if (resValue[stat_name] != null || resValue[stat_name] != undefined) 
                {
                  values[stat_name].push([ts, resValue[stat_name]]);
                }
              });
            }
          }
      });
      $.each(stats, function(i, stat_name)
      {
        obj_db_AreaSpline_ioOps_Data.series[count] = 
        {
          name: targetName,
          data: values[stat_name],
        };
      });
    }
  })
  .error(function(event) 
  {
    // Display of appropriate error message
  })
  .complete(function(event)
  {
    obj_db_AreaSpline_ioOps_Data.chart.renderTo = "db_iopsSpline";
    if(isZoom == 'true') 
    {
      renderZoomDialog(obj_db_AreaSpline_ioOps_Data);
    }
    /*$.each(stats, function(i, stat_name) 
    {
      obj_db_AreaSpline_ioOps_Data.series[i].data = values[stat_name];
    });*/
    chart = new Highcharts.Chart(obj_db_AreaSpline_ioOps_Data);
  });
}
/*****************************************************************************
 * Function to plot heat map
 * Params - fetchmatrics, isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
db_HeatMap_Data = function(fetchmetrics, isZoom)
{
  var categories = [];
  obj_db_HeatMap_Data = JSON.parse(JSON.stringify(chartConfig_HeatMap));
  obj_db_HeatMap_Data.chart.renderTo = "db_heatMapDiv";
  var ostName, count =0, color;
  $.post(db_HeatMap_Data_Api_Url,
  {
    fetchmetrics: "cpu", endtime: endTime, datafunction: "Average", 
    starttime: startTime, filesystem: ""
  })
  .success(function(data, textStatus, jqXHR) 
  {   
    if(data.success)
    {
      var response = data.response;
      var clientMountData = [];
      var valueArray = [];
      $.each(response, function(resKey, resValue) 
      {
        if (ostName != resValue.ost && ostName !='')
        {
          obj_db_HeatMap_Data.series[count] = 
          {
              name: ostName,
              color: color,
        			data: clientMountData,
        			marker: {
        		       symbol: 'square',
                       lineWidth: 0.5,
                       lineColor: 'black',
        		       radius: 8
        		  }
           };
	         clientMountData = [];
	         categories = [];
	         valueArray = [];
	         count++;
	         ostName = resValue.ost;

           valueArray.push(resValue.timestamp);
           valueArray.push(resValue.cpu);

           clientMountData.push(valueArray);

           categories.push(resValue.timestamp);
        }
        else
        {
          valueArray = [];
	        ostName = resValue.ost;
	        color = resValue.color;

	        valueArray.push(resValue.timestamp);
	        valueArray.push(resValue.cpu);

	        clientMountData.push(valueArray);

	        categories.push(resValue.timestamp);
	      }
      });
    }
    obj_db_HeatMap_Data.series[count] = { name: ostName, color: color, data: clientMountData, marker: { symbol: 'square',radius: 8 } };
  })
  .error(function(event) 
  {
    // Display of appropriate error message
  })
  .complete(function(event)
  {
    obj_db_HeatMap_Data.xAxis.categories = categories;
    obj_db_HeatMap_Data.xAxis.labels = 
    {
      rotation: 310,step: 4,style:{fontSize:'8px', fontWeight:'regular'}
    }
    
    if(isZoom == 'true')
    {
      renderZoomDialog(obj_db_HeatMap_Data);
    }
    chart = new Highcharts.Chart(obj_db_HeatMap_Data);
  });
}
/*****************************************************************************
 * Function to plot heat map for CPU Usage
 * Params - fetchmatrics, isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
db_HeatMap_CPUData = function(fetchmetrics, isZoom)
{
  plot_bands_ost = [];
  ost_count = 1;
  obj_db_HeatMap_CPUData = JSON.parse(JSON.stringify(chartConfig_HeatMap));
  obj_db_HeatMap_CPUData.chart.renderTo = "db_heatMapDiv";
  var hostName='' , count =0, color;
  $.post("/api/get_server_stats_heatmap/",
  {
    fetchmetrics: cpuMemoryFetchMatric, endtime: endTime, datafunction: "Average", 
     starttime: startTime, filesystem: ""
  })
  .success(function(data, textStatus, jqXHR) 
  {
    if(data.success)
    {
      var response = data.response;
      var values = [];
      $.each(response, function(resKey, resValue) 
      {
        if (hostName != resValue.host && hostName !='')
        {
          plot_bands_ost.push ({from: ost_count,to: ost_count,color: resValue.color_gred, 
                                label: { text: hostName + ost_count }});
          ost_count++;
        }
        hostName = resValue.host
        ts = resValue.timestamp * 1000;
        colorCode = resValue.color_gred;
        values.push([ts,ost_count]); 
      });
      plot_bands_ost.push ({from: ost_count,to: ost_count,color: colorCode,
                            label: { text: hostName + ost_count }});
    }
    obj_db_HeatMap_CPUData.yAxis.plotBands = plot_bands_ost;
    obj_db_HeatMap_CPUData.series[count] = { name:'', data: values, marker: { symbol: 'square',radius: 8 }};
  })
  .error(function(event) 
  {
    // Display of appropriate error message
  })
  .complete(function(event)
  {
    obj_db_HeatMap_CPUData.chart.renderTo = "db_heatMapDiv";
    if(isZoom == 'true')
    {
      renderZoomDialog(obj_db_HeatMap_CPUData);
    } 
    chart = new Highcharts.Chart(obj_db_HeatMap_CPUData);
  });
}

/*****************************************************************************
 * Function to plot heat map for CPU Usage
 * Params - fetchmatrics, isZoom
 * Return - Returns the graph plotted in container
*****************************************************************************/
db_HeatMap_ReadWriteData = function(fetchmetrics, isZoom)
{
  plot_bands_ost = [];
  ost_count = 1;
  obj_db_HeatMap_CPUData = JSON.parse(JSON.stringify(chartConfig_HeatMap));
  obj_db_HeatMap_CPUData.chart.renderTo = "db_heatMapDiv";
  var targetName='' , count =0, color;
  $.post("/api/get_fs_stats_heatmap/",
  {
    fetchmetrics: readWriteFetchMatric.join(" "), endtime: endTime, datafunction: "Average", 
     starttime: startTime, filesystem: "", targetkind:"OST"
  })
  .success(function(data, textStatus, jqXHR) 
  {
    if(data.success)
    {
      var response = data.response;
      var values = [];
      $.each(response, function(resKey, resValue) 
      {
        if (targetName != resValue.host && targetName !='')
        {
          plot_bands_ost.push ({from: ost_count,to: ost_count,color: 'rgba(68, 170, 213, 0.1)', 
                                label: { text: targetName + ost_count }});
          ost_count++;
        }
        targetName = resValue.target
        ts = resValue.timestamp * 1000;
        values.push([ts,ost_count]); 
      });
       plot_bands_ost.push ({from: ost_count,to: ost_count,color: 'rgba(68, 170, 213, 0.1)',
                                label: { text: targetName + ost_count }});
    }
    obj_db_HeatMap_CPUData.yAxis.plotBands = plot_bands_ost;
    obj_db_HeatMap_CPUData.series[count] = { name:'', data: values, marker: { symbol: 'square',radius: 8 }};
  })
  .error(function(event) 
  {
    // Display of appropriate error message
  })
  .complete(function(event)
  {
    obj_db_HeatMap_CPUData.chart.renderTo = "db_heatMapDiv";
    if(isZoom == 'true')
    {
      renderZoomDialog(obj_db_HeatMap_CPUData);
    } 
    chart = new Highcharts.Chart(obj_db_HeatMap_CPUData);
  });
}

/****************************************************************************
 * Function for zooming functionality for all graphs
*****************************************************************************/
renderZoomDialog = function(object)
{
  object.xAxis.labels={style:{fontSize:'12px'}};
  object.yAxis.labels={style:{fontSize:'12px', fontWeight:'bold'}};
  object.chart.width = "780";
  object.chart.height = "360";
  object.chart.style.height = "360";
  object.chart.style.width = "100%";
  object.chart.renderTo = "zoomDialog";
  object.legend.enabled = true;
}
/*****************************************************************************
 * Function for setting title for zoom dialog
*****************************************************************************/
setZoomDialogTitle = function(titleName)
{
  $('#zoomDialog').dialog('option', 'title', titleName);
  $('#zoomDialog').dialog('open');
  $('#zoomDialog').html("<img src='/static/images/wait_progress.gif' style='align:center;'/>");
}
/*****************************************************************************
 * Function to start polling for all graphs on dashboard landing page
*****************************************************************************/
initDashboardPolling = function()
{
  if(isPollingFlag)
  {
    dashboardPollingInterval = self.setInterval(function()
    {
      db_Bar_SpaceUsage_Data('false');
      db_Line_connectedClients_Data('false');
      db_LineBar_CpuMemoryUsage_Data('false');
      db_Area_ReadWrite_Data('false');
      db_Area_mdOps_Data('false');
    }, 10000);
  }
  else
  {
    db_Bar_SpaceUsage_Data('false');
    db_Line_connectedClients_Data('false');
    db_LineBar_CpuMemoryUsage_Data('false');
    db_Area_ReadWrite_Data('false');
    db_Area_mdOps_Data('false');
  }
}
/*****************************************************************************
 * Function to clear dashboard pooling intervals
*****************************************************************************/
clearAllIntervals = function()
{
  clearInterval(dashboardPollingInterval);
  clearInterval(fsPollingInterval);
}
/******************************************************************************/
