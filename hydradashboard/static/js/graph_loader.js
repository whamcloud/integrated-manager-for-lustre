/*******************************************************************************/
// File name: custom_dashboard.js
// Description: Plots all the graphs for dashboard landing page.
//------------------Configuration functions--------------------------------------
// 1) chartConfig_Bar_SpaceUsage    -  Bar chart configuration for space and inodes graph
// 2) chartConfig_Line_clientConnected  -  Line chart configuration for number of clients connected
// 3) chartConfig_LineBar_CPUMemoryUsage  -  Column chart for cpu usage and line chart for memory usage
// 4) chartConfig_Area_ReadWrite    -  Area graph for disk reads and writes
// 5) chartConfig_Area_mdOps      -  Area graph for mdOP/s
// 6) chartConfig_HeatMap      -  HeatMap graph
//------------------ Data Loader functions--------------------------------------
// 1) db_Bar_SpaceUsage_Data(isZoom)
// 2) db_Line_connectedClients_Data(isZoom)
// 3) db_LineBar_CpuMemoryUsage_Data(isZoom)
// 4) db_Area_ReadWrite_Data(isZoom)
// 5) db_Area_mdOps_Data(isZoom)
// 6) db_HeatMap_Data
/*******************************************************************************/
var spaceUsageFetchMatric = "kbytestotal kbytesfree filestotal filesfree";
var clientsConnectedFetchMatric = "num_exports";
var cpuMemoryFetchMatric = "cpu_usage cpu_total mem_MemFree mem_MemTotal";
var readWriteFetchMatric = ["stats_read_bytes", "stats_write_bytes"];
var mdOpsFetchmatric = ["stats_close", "stats_getattr", "stats_getxattr", "stats_link", "stats_mkdir", "stats_mknod", "stats_open", "stats_rename", "stats_rmdir", "stats_setattr", "stats_statfs", "stats_unlink"]
var dashboardPollingInterval;

var db_Bar_SpaceUsage_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var db_Line_connectedClients_Data_Api_Url = "/api/get_fs_stats_for_client/";
var db_LineBar_CpuMemoryUsage_Data_Api_Url = "/api/get_fs_stats_for_server/";
var db_Area_ReadWrite_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var db_Area_mdOps_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var db_HeatMap_Data_Api_Url = "/api/get_fs_ost_heatmap/";

var startTime = "5";
var endTime = "";

var chartConfig_Bar_SpaceUsage = {    
  chart:{
  renderTo: '',
  marginLeft: '50',
  width: '300',
  height: '200',
  style:{ width:'100%',  height:'200', position: 'inherit' },
  marginBottom: 35,
  defaultSeriesType: 'column',
  backgroundColor: '#f9f9ff',
  },
  colors: [
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
  yAxis:{max:100, min:0, startOnTick:false, title:{text:'Percentage'}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
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

var chartConfig_Line_clientConnected = {
  chart: {
    renderTo: 'container3',
    marginLeft: '50',
    width: '300',
    height: '200',
    style:{ width:'100%',  height:'210', position: 'inherit' },
    marginBottom: 35,
    zoomType: 'xy',
    backgroundColor: '#f9f9ff',
  },
  title: {
     text: 'Connected Clients',
     style: { fontSize: '12px' },
  },
  xAxis: {
    type:'datetime',
    //labels: {rotation: 310,step: 4,style:{fontSize:'8px', fontWeight:'regular'}}
  },
  yAxis: {
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
  tooltip: {
     formatter: function() {
         return 'Time: '+this.x +'No. Of Exports: '+ this.y;
     }
  },
  legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
  credits:{ enabled:false },
  series: [{
     name: '',
    data: []
  }],
    plotOptions: {
series:{marker: {enabled: false}}
},

 };

var chartConfig_LineBar_CPUMemoryUsage = {
  chart: {
   renderTo: 'avgCPUDiv',
   marginLeft: '50',
   width: '300',
   height: '200',
   style:{ width:'100%',  height:'210', position: 'inherit' },
   marginBottom: 35,
   zoomType: 'xy',
   backgroundColor: '#f9f9ff',
  },
  title: {
    text: 'Server CPU and Memory',
    style: { fontSize: '12px' },
  },
  xAxis: {
    //title: 'Time (hh:mm:ss)',
    type:'datetime',
    //labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}
  },
  yAxis: [{
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
  }],
  legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
  credits:{ enabled:false },
  plotOptions:{
    series:{marker: {enabled: false}},
      column:{
      pointPadding: 0.0,
      shadow: false,
      groupPadding: 0.0,
      borderWidth: 0.0
    }
  },
  series: [{
      type: 'column',
      data: [],
      name: 'CPU Usage',
      yAxis: 1
    },{
      type: 'line',
      data: [],
      name: 'Memory',
    }]
};

var chartConfig_Area_ReadWrite = {
      chart: {
      renderTo: 'avgMemoryDiv',
      defaultSeriesType: 'area',
      marginLeft: '50',
      width: '300',
      height: '200',
      style:{ width:'100%',  height:'210', position: 'inherit' },
      marginRight: 0,
      marginBottom: 35,
      backgroundColor: '#f9f9ff',
      zoomType: 'xy'
      },
      colors: [
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
      title: {
       text: 'Read vs Writes',
       style: { fontSize: '12px' },
      },
     xAxis: {
      //title: 'Time (hh:mm:ss)',
      type:'datetime',  
      //labels: {rotation: 310,step: 4,style:{fontSize:'8px', fontWeight:'regular'}}
     },
     yAxis: {
      title: {text: 'KB'}
     },
     tooltip: {
       formatter: function() {
        return ''+
          this.series.name +': '+ this.y +'';
       }
     },
     legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
     credits:{ enabled:false },
     plotOptions:{ 
       series:{marker: {enabled: false}} },
       credits: { enabled: false },
       series: [{ name: 'Read', data: []}, { name: 'Write',data: []}]
     }

var chartConfig_Area_mdOps  = {
      chart: {
      defaultSeriesType: 'area',
      marginLeft: '50',
      height: '200',
      style:{ width:'100%',  height:'210', position: 'inherit' },
      marginRight: 0,
      marginBottom: 35,
      zoomType: 'xy',
      backgroundColor: '#f9f9ff'
      },
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
      title: {
       text: 'Metadata ops',
       style: { fontSize: '12px' },
      },
     xAxis: {
        type: 'datetime'
      },
      yAxis: {
       title: {
        text: 'MD op/s'
       },
      },
      tooltip: {
       formatter: function() {
        return ''+
          this.x +': '+ Highcharts.numberFormat(this.y, 0, ',') +' ';
       }
      },
      legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
      credits:{ enabled:false },
      plotOptions: {
     series:{marker: {enabled: false}},
       area: {
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




var chartConfig_HeatMap = {
   chart: {
       renderTo: '', 
       defaultSeriesType: 'scatter',
       marginLeft: '50',
      width: '1150',
       height: '200',
      style:{ width:'100%',  height:'210', position: 'inherit' },
       marginRight: 0,
       marginBottom: 35,
       zoomType: 'xy'
    },
    title: {
       text: 'Heat Map',
       style: { fontSize: '12px' }
    },
    xAxis: {
       title: {
        enabled: true,
        text: ''
       },
       startOnTick: true,
       endOnTick: true,
       showLastLabel: true
    },
    yAxis: {
       title: {
        text: ''
       },max:100, min:0, startOnTick:false, 
    },
    tooltip: {
       formatter: function() {
           return ''+
         this.x +' , '+ this.y +' ';
       }
    },
    legend: {
     enabled : false,
       layout: 'vertical',
       align: 'left',
       verticalAlign: 'top',
       x: 100,
       y: 70,
       floating: true,
       backgroundColor: '#FFFFFF',
       borderWidth: 1
    },
    plotOptions: {
       scatter: {
        marker: {
         radius: 5,
         states: {
          hover: {
             enabled: true,
             lineColor: 'rgb(100,100,100)'
          }
         }
        },
        states: {
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
/*****************************************************************************/
// Function for space usage for all file systems  - Stacked Bar Chart
// Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
// Return - Returns the graph plotted in container
/*****************************************************************************/

  db_Bar_SpaceUsage_Data = function(isZoom)
  {
  var free=0,used=0;
    var freeData = [],usedData = [],categories = [],freeFilesData = [],totalFilesData = [];
    $.post(db_Bar_SpaceUsage_Data_Api_Url,
    {targetkind: "OST", datafunction: "Average", fetchmetrics: spaceUsageFetchMatric, 
    "starttime": "", "filesystem": "", "endtime": ""})
    .success(function(data, textStatus, jqXHR) 
    {   
    if(data.success)
    {
      var response = data.response;
      var totalDiskSpace=0,totalFreeSpace=0,totalFiles=0,totalFreeFiles=0;
      $.each(response, function(resKey, resValue) 
      {
      //alert(resKey+"=="+resValue.filesystem);
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
    .complete(function(event){
    obj_db_Bar_SpaceUsage_Data = JSON.parse(JSON.stringify(chartConfig_Bar_SpaceUsage));
    obj_db_Bar_SpaceUsage_Data.chart.renderTo = "container";
    obj_db_Bar_SpaceUsage_Data.xAxis.categories = categories;
      obj_db_Bar_SpaceUsage_Data.title.text="All File System Space Usage";
      obj_db_Bar_SpaceUsage_Data.series = [
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
/*****************************************************************************/
// Function for number of clients connected  - Line Chart
// Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
// Return - Returns the graph plotted in container
/*****************************************************************************/
  db_Line_connectedClients_Data = function(isZoom)
  {
    obj_db_Line_connectedClients_Data = JSON.parse(JSON.stringify(chartConfig_Line_clientConnected));
    var clientMountData = [];
    var count=0;
    var fileSystemName = "";
      $.post(db_Line_connectedClients_Data_Api_Url,
      {"fetchmetrics": clientsConnectedFetchMatric, "endtime": endTime, "datafunction": "Average", 
       "starttime": startTime, "filesystem": ""})
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

/*****************************************************************************/
// Function for cpu and memory usage - Line + Column Chart
// Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
// Return - Returns the graph plotted in container
/*****************************************************************************/
 db_LineBar_CpuMemoryUsage_Data = function(isZoom)
{
  var count = 0;
  var cpuData = [],categories = [], memoryData = [];
  obj_db_LineBar_CpuMemoryUsage_Data = JSON.parse(JSON.stringify(chartConfig_LineBar_CPUMemoryUsage));
  $.post(db_LineBar_CpuMemoryUsage_Data_Api_Url,
    {"fetchmetrics": cpuMemoryFetchMatric, "endtime": endTime, "datafunction": "Average", 
    "starttime": startTime, "filesystem": ""})
    .success(function(data, textStatus, jqXHR) 
    {
      var hostName='';
      var avgCPUApiResponse = data;
      if(avgCPUApiResponse.success)
      {
        var response = avgCPUApiResponse.response;
        $.each(response, function(resKey, resValue) 
        {
          if(resValue.host != undefined)
          {
            if (resValue.cpu_usage != undefined || resValue.cpu_total != undefined)          
            {
              ts = resValue.timestamp * 1000
              cpuData.push([ts,((resValue.cpu_usage*100)/resValue.cpu_total)]);
              memoryData.push([ts,(resValue.mem_MemTotal - resValue.mem_MemFree)]);
            }
          }
        });
      }
     })
     .error(function(event) {
       // Display of appropriate error message
     })
     .complete(function(event){
        //obj_db_LineBar_CpuMemoryUsage_Data.xAxis.categories = categories;
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

/*****************************************************************************/
//Function for disk read and write - Area Chart
//Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
//Return - Returns the graph plotted in container
/*****************************************************************************/
db_Area_ReadWrite_Data = function(isZoom)
{
  obj_db_Area_ReadWrite_Data = JSON.parse(JSON.stringify(chartConfig_Area_ReadWrite));
  var values = new Object();
  var stats = readWriteFetchMatric;
  $.each(stats, function(i, stat_name){
    values[stat_name] = [];
  });
  $.post(db_Area_ReadWrite_Data_Api_Url,{"targetkind": "OST", "datafunction": "Average", "fetchmetrics": stats.join(" "),
    "starttime": startTime, "filesystem": "", "endtime": endTime})
      .success(function(data, textStatus, jqXHR) {
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
              $.each(stats, function(i, stat_name) {
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
      $.each(stats, function(i, stat_name) {
        obj_db_Area_ReadWrite_Data.series[i].data = values[stat_name];
      });
      if(isZoom == 'true')
      {
        renderZoomDialog(obj_db_Area_ReadWrite_Data);
      }
      chart = new Highcharts.Chart(obj_db_Area_ReadWrite_Data);
    });
}

/*****************************************************************************/
//Function for mdOps - Area Chart
//Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Area_mdOps_Data = function(isZoom)
 {
     // var mdOpsFetchmatric = ["stats_close", "stats_getattr", "stats_getxattr", "stats_link", "stats_mkdir", "stats_mknod", "stats_open", "stats_rename", "stats_rmdir", "stats_setattr", "stats_statfs", "stats_unlink"]
    var closeData = [], getattrData = [], getxattrData = [], linkData = [], mkdirData = [], mknodData = [], openData = [], renameData = [], rmdirData = [], setattrData = [], statfsData = [], unlinkData = [];
    obj_db_Area_mdOps_Data = JSON.parse(JSON.stringify(chartConfig_Area_mdOps));

    var values = new Object();
    var stats = mdOpsFetchmatric;
    $.each(stats, function(i, stat_name) {
      values[stat_name] = [];
    });
    $.post(db_Area_mdOps_Data_Api_Url,{"targetkind": "MDT", "datafunction": "Average", "fetchmetrics": stats.join(" "),
       "starttime": startTime, "filesystem": "", "endtime": endTime})
     .success(function(data, textStatus, jqXHR) {
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
           $.each(stats, function(i, stat_name) {
             if (resValue[stat_name] != null || resValue[stat_name] != undefined) {
             values[stat_name].push([ts, resValue[stat_name]])
             }
           });
           }
       });
         }
     })
     .error(function(event) {
       // Display of appropriate error message
     })
     .complete(function(event){
       obj_db_Area_mdOps_Data.chart.renderTo = "avgReadDiv";
        if(isZoom == 'true') {
          renderZoomDialog(obj_db_Area_mdOps_Data);
        }

        $.each(stats, function(i, stat_name) {
          obj_db_Area_mdOps_Data.series[i].data = values[stat_name];
        });
        
        if(isZoom == 'true')
        {
           renderZoomDialog(obj_db_Area_mdOps_Data);
        }
        
        chart = new Highcharts.Chart(obj_db_Area_mdOps_Data);
    });
}
/*****************************************************************************/
//Function to plot heat map
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_HeatMap_Data = function(isZoom)
 {
   obj_db_HeatMap_Data = JSON.parse(JSON.stringify(chartConfig_HeatMap));
   obj_db_HeatMap_Data.chart.renderTo = "db_heatMapDiv";
   var ostName, count =0;
   $.post(db_HeatMap_Data_Api_Url,
      {"fetchmetrics": "cpu", "endtime": endTime, "datafunction": "Average", 
       "starttime": startTime, "filesystem": ""})
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
            obj_db_HeatMap_Data.series[count] = {
              name: ostName,
              color: 'rgba(0, 128, 0, .7)',
              data: clientMountData
            };
            clientMountData = [];
            categories = [];
            valueArray = [];
            count++;
            ostName = resValue.ost;
          
            valueArray.push(resValue.timestamp * 1000);
            valueArray.push(resValue.cpu);
            
            clientMountData.push(valueArray);
            
            categories.push(resValue.timestamp * 1000);
           }
           else
           {
          valueArray = [];
          ostName = resValue.ost;
          
          valueArray.push(resValue.timestamp * 1000);
            valueArray.push(resValue.cpu);
            
            clientMountData.push(valueArray);
            
            categories.push(resValue.timestamp * 1000);
           }
            
            
          });
        }
        obj_db_HeatMap_Data.series[count] = { name: ostName, color: 'rgba(0, 128, 0, .7)', data: clientMountData };
        
        
      })
      .error(function(event) 
      {
         // Display of appropriate error message
      })
      .complete(function(event){
        obj_db_HeatMap_Data.xAxis.categories = categories;
        obj_db_HeatMap_Data.xAxis.labels = {
          rotation: 310,step: 4,style:{fontSize:'8px', fontWeight:'regular'}
        }
        chart = new Highcharts.Chart(obj_db_HeatMap_Data);
      });
}

/*****************************************************************************/
//Function for zooming functionality for graphs
/*****************************************************************************/
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
/*****************************************************************************/
//Function for setting title for zoom dialog
/*****************************************************************************/
  setZoomDialogTitle = function(titleName)
  {
    $('#zoomDialog').empty();
    $('#zoomDialog').dialog('option', 'title', titleName);
    $('#zoomDialog').dialog('open');
    $('#zoomDialog').html("<img src='/static/images/wait_progress.gif' style='align:center;'/>");
  }
 
/*****************************************************************************/
//Function to start polling dashboard landing page
/*****************************************************************************/
  initDashboardPolling = function()
  {
    db_Bar_SpaceUsage_Data('false');
    db_Line_connectedClients_Data('false');
    db_LineBar_CpuMemoryUsage_Data('false');
    db_Area_ReadWrite_Data('false');
    db_Area_mdOps_Data('false');
    //db_HeatMap_Data('false');
  }
  
  clearAllIntervals = function(){
  clearInterval(dashboardPollingInterval);
  }
/******************************************************************************/
// Function to show OSS/OST dashboards
/******************************************************************************/
  function showFSDashboard(){
	  loadFSContent($('#ls_filesystem').val());
  }

  function showOSSDashboard(){
	  loadOSSContent($('#ls_filesystem').val(), $('#ls_oss').val());
  }
/******************************************************************************/
