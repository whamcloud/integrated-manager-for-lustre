/*******************************************************************************/
// File name: custom_filesystem.js
// Description: Plots all the graphs for file system dashboard

//------------------ Data Loader functions--------------------------------------
// 1) fs_Bar_SpaceUsage_Data(isZoom)
// 2) fs_Line_connectedClients_Data(isZoom)
// 3) fs_LineBar_CpuMemoryUsage_Data(isZoom)
// 4) fs_Area_ReadWrite_Data(isZoom)
// 5) fs_Area_mdOps_Data(isZoom)
// 6) fs_HeatMap_Data
/********************************************************************************/
var fs_Bar_SpaceUsage_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var fs_Line_connectedClients_Data_Api_Url = "/api/get_fs_stats_for_client/";
var fs_LineBar_CpuMemoryUsage_Data_Api_Url = "/api/get_fs_stats_for_server/";
var fs_Area_ReadWrite_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var fs_Area_mdOps_Data_Api_Url = "/api/get_fs_stats_for_targets/";
var fs_HeatMap_Data_Api_Url = "/api/get_fs_ost_heatmap/";

/*****************************************************************************/
//Function for space usage for selected file systems - Pie Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
fs_Bar_SpaceUsage_Data = function(fsName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
{
  var free=0,used=0;
  var freeData = [],usedData = [],categories = [],freeFilesData = [],totalFilesData = [];
  $.post(fs_Bar_SpaceUsage_Data_Api_Url,
    {targetkind: targetKind, datafunction: dataFunction, fetchmetrics: fetchMetrics, 
     starttime: "", filesystem: fsName, endtime: ""})
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
	  obj_fs_Bar_SpaceUsage_Data = JSON.parse(JSON.stringify(chartConfig_Bar_SpaceUsage));
	  obj_fs_Bar_SpaceUsage_Data.chart.renderTo = "fs_container2";
	  obj_fs_Bar_SpaceUsage_Data.xAxis.categories = categories;
      obj_fs_Bar_SpaceUsage_Data.title.text="All File System Space Usage";
      obj_fs_Bar_SpaceUsage_Data.series = [
        {data: freeData, stack: 0, name: 'Free Space'}, {data: usedData, stack: 0, name: 'Used Space'},					// first stack
        {data: freeFilesData, stack: 1, name: 'Free Files'}, {data: totalFilesData, stack: 1, name: 'Used Files'}		// second stack
      ];		
      if(isZoom == 'true')
	  {
        renderZoomDialog(obj_fs_Bar_SpaceUsage_Data);
	  }
      chart = new Highcharts.Chart(obj_fs_Bar_SpaceUsage_Data);
    });
}
/*****************************************************************************/
// Function for number of clients connected	- Line Chart
// Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
// Return - Returns the graph plotted in container
/*****************************************************************************/
fs_Line_connectedClients_Data = function(fsName, sDate, endDate, dataFunction, fetchMetrics, isZoom)
{
  obj_fs_Line_connectedClients_Data = JSON.parse(JSON.stringify(chartConfig_Line_clientConnected));
  var clientMountData = [];
  var count=0;
  var fileSystemName = "";
  $.post(fs_Line_connectedClients_Data_Api_Url,
    {datafunction: dataFunction, fetchmetrics: fetchMetrics, starttime: sDate, filesystem: fsName, endtime: endDate})
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
            	 obj_fs_Line_connectedClients_Data.series[count] =
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
           obj_fs_Line_connectedClients_Data.series[count] = { name: fileSystemName, data: clientMountData}; 
         }
       })
     .error(function(event) 
     {
       // Display of appropriate error message
     })
     .complete(function(event)
     {
       obj_fs_Line_connectedClients_Data.chart.renderTo = "fs_container3";
       if(isZoom == 'true')
  	   {
         renderZoomDialog(obj_fs_Line_connectedClients_Data);
  	   }
       chart = new Highcharts.Chart(obj_fs_Line_connectedClients_Data);
     });
}
/*****************************************************************************/
// Function for cpu and memory usage - Line + Column Chart
// Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
// Return - Returns the graph plotted in container
/*****************************************************************************/
fs_LineBar_CpuMemoryUsage_Data = function(fsName, sDate, endDate, dataFunction, targetkind,fetchMetrics, isZoom)
{
  var count = 0;
  var cpuData = [], memoryData = [];
  obj_fs_LineBar_CpuMemoryUsage_Data = JSON.parse(JSON.stringify(chartConfig_LineBar_CPUMemoryUsage));
  $.post(fs_LineBar_CpuMemoryUsage_Data_Api_Url,
    {datafunction: dataFunction, fetchmetrics: fetchMetrics, starttime: sDate, filesystem: fsName, endtime: endDate})
  .success(function(data, textStatus, jqXHR) 
  {
    var hostName='';
    var fsCPUMemoryApiResponse = data;
    if(fsCPUMemoryApiResponse.success)
    {
      var response = fsCPUMemoryApiResponse.response;
      $.each(response, function(resKey, resValue) 
      {
        if(resValue.host != undefined)
        {
	      if (resValue.cpu_usage != null || resValue.cpu_usage != undefined || resValue.mem_MemTotal != null || resValue.mem_MemTotal != undefined)
          {
            ts = resValue.timestamp * 1000
            cpuData.push([ts,((resValue.cpu_usage*100)/resValue.cpu_total)]);
	        memoryData.push([ts,(resValue.mem_MemTotal - resValue.mem_MemFree)]);
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
    obj_fs_LineBar_CpuMemoryUsage_Data.chart.renderTo = "fs_avgCPUDiv";
    if(isZoom == 'true')
    {
      renderZoomDialog(obj_fs_LineBar_CpuMemoryUsage_Data);
    }
    obj_fs_LineBar_CpuMemoryUsage_Data.series[0].data = cpuData;
    obj_fs_LineBar_CpuMemoryUsage_Data.series[1].data = memoryData;
    chart = new Highcharts.Chart(obj_fs_LineBar_CpuMemoryUsage_Data);
  });
}

/*****************************************************************************/
//Function for disk read and write - Area Chart
//Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
//Return - Returns the graph plotted in container
/*****************************************************************************/
fs_Area_ReadWrite_Data = function(fsName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
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
                      values[stat_name].push([ts, (0 - (resValue[stat_name]/1024))]);
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
      obj_db_Area_ReadWrite_Data.chart.renderTo = "fs_avgMemoryDiv";
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
fs_Area_mdOps_Data = function(fsName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
{
	var readData = [], writeData = [], statData = [], closeData = [], openData = [];
    obj_db_Area_mdOps_Data = JSON.parse(JSON.stringify(chartConfig_Area_mdOps));

    var values = new Object();
    var stats = mdOpsFetchmatric;
    $.each(stats, function(i, stat_name) {
      values[stat_name] = [];
    });
    $.post(db_Area_mdOps_Data_Api_Url,{"targetkind": targetKind, "datafunction": dataFunction, "fetchmetrics": stats.join(" "),
       "starttime": startTime, "filesystem": fsName, "endtime": endTime})
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
       obj_db_Area_mdOps_Data.chart.renderTo = "fs_avgReadDiv";
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
 fs_HeatMap_Data = function(isZoom)
 {
	 var obj_db_HeatMap_Data = JSON.parse(JSON.stringify(chartConfig_HeatMap));
	 obj_db_HeatMap_Data.chart.renderTo = "fs_heatMapDiv";
	 var ostName, count =0;
	 $.post(fs_HeatMap_Data_Api_Url,
	          {"fetchmetrics": "cpu", "endtime": "2011-10-17 19:46:58.912171", "datafunction": "Average", 
	           "starttime": "2011-10-17 19:56:58.912150", "filesystem": ""})
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
	      		        
	      		          valueArray.push(resValue.timestamp);
	      		          valueArray.push(resValue.cpu);
	      		          
	      		          clientMountData.push(valueArray);
	      		          
	      		          categories.push(resValue.timestamp);
	      			       }
	      			       else
	      			       {
	      			    	valueArray = [];
	      			    	ostName = resValue.ost;
	      			    	
	      			    	valueArray.push(resValue.timestamp);
		      		        valueArray.push(resValue.cpu);
		      		        
		      		        clientMountData.push(valueArray);
	      			        
		      		        categories.push(resValue.timestamp);
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
	 
	  	if(isZoom == 'true')
	   	{
	   	  renderZoomDialog(obj_db_HeatMap_Data);
	   	}
	 	chart = new Highcharts.Chart(obj_db_HeatMap_Data);
      
}
/********************************************************************************/
 
 loadFileSystemSummary = function (fsName){
	 var innerContent = "";
	 $('#fileSystemSummaryTbl').html("<tr><td width='100%' align='center' height='180px'><img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' /></td></tr>");
	 $.post("/api/getfilesystem/",{filesystem: fsName})
     .success(function(data, textStatus, jqXHR) {
         if(data.success)
         {
             var response = data.response;
             $.each(response, function(resKey, resValue) {
            	 innerContent = innerContent + 
            	 "<tr><td class='greybgcol'>MGS :</td><td class='tblContent greybgcol'>"+resValue.mgsname+"</td><td>&nbsp;</td><td>&nbsp;</td></tr>"+
                 "<tr><td class='greybgcol'>MDS:</td><td class='tblContent greybgcol'>"+resValue.mdsname+"</td><td class='greybgcol'>Failover:</td><td class='tblContent txtleft'>NA</td></tr>"+
                 "<tr><td class='greybgcol'>Standby MDS:</td><td class='tblContent greybgcol'>--</td><td>&nbsp;</td><td>&nbsp;</td></tr>"+
                 "<tr><td class='greybgcol'>Total OSSs: </td><td class='tblContent greybgcol'>"+resValue.noofoss+" </td><td class='greybgcol'>Total OSTs:</td><td class='tblContent txtleft'>"+resValue.noofost+"</td></tr>"+
                 "<tr><td class='greybgcol'>Total Capacity: </td><td class='tblContent greybgcol'>"+resValue.kbytesused+" </td><td class='greybgcol'>Total Free:</td><td class='tblContent txtleft'>"+resValue.kbytesfree+"</td></tr>"+
                 "<tr><td class='greybgcol'>Files Total: </td><td class='tblContent greybgcol'>"+resValue.mdtfileused+" </td><td class='greybgcol'>Files Free:</td><td class='tblContent txtleft'>"+resValue.mdtfilesfree+"</td></tr>"+
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
         }
    })
	.error(function(event) {
	})
	.complete(function(event){
		$('#fileSystemSummaryTbl').html(innerContent);
	});
 }

/*********************************************************************************************/
 
 	initFileSystemPolling = function()
	{
		 fs_Bar_SpaceUsage_Data($('#fsSelect').val(), "", "", "Average", "OST", spaceUsageFetchMatric, false);
	
	     fs_Line_connectedClients_Data($('#fsSelect').val(), startTime, endTime, "Average", clientsConnectedFetchMatric, false);
	 
	     fs_LineBar_CpuMemoryUsage_Data($('#fsSelect').val(), startTime, endTime, "Average", "OST", cpuMemoryFetchMatric, false);
	
	     fs_Area_ReadWrite_Data($('#fsSelect').val(), startTime, endTime, "Average", "MDT", readWriteFetchMatric, false);
	
	     fs_Area_mdOps_Data($('#fsSelect').val(), startTime, endTime, "Average", "MDT", mdOpsFetchmatric, false);
	}
 
/*********************************************************************************************/
