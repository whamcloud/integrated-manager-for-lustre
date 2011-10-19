/**************************************************************************/
//File Name - custome_oss.js
//Description - Contains function to plot pie, line and bar charts on OSS Screen
//Functions - 
//---------------------Data Loaders function-------------------------------
//	1) oss_LineBar_CpuMemoryUsage_Data(fsName, sDate, endDate, dataFunction, fetchMetrics, isZoom)
//	2) oss_Area_ReadWrite_Data(fsName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
/******************************************************************************/

/******************************************************************************/
// Function for cpu and memory usage - Line + Column Chart
// Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
// Return - Returns the graph plotted in container
/*****************************************************************************/
 oss_LineBar_CpuMemoryUsage_Data = function(fsName, sDate, endDate, dataFunction, fetchMetrics, isZoom)
 {
	    var count = 0;
        var cpuData = [],categories = [], memoryData = [];
		obj_db_LineBar_CpuMemoryUsage_Data = JSON.parse(JSON.stringify(chartConfig_LineBar_CPUMemoryUsage));
		$.post("/api/get_fs_stats_for_server/",
		  {datafunction: dataFunction, fetchmetrics: fetchMetrics, starttime: sDate, filesystem: fsName, endtime: endDate})
         .success(function(data, textStatus, jqXHR) 
          {
            var hostName='';
            var avgCPUApiResponse = data;
            if(avgCPUApiResponse.success)
            {
                 var response = avgCPUApiResponse.response;
                 $.each(response, function(resKey, resValue) 
                 {
                	cpuData.push(resValue.cpu_usage);
                	memoryData.push(resValue.mem_MemTotal - resValue.mem_MemFree);
                	
			        categories.push(resValue.timestamp);
			     });
            }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_db_LineBar_CpuMemoryUsage_Data.xAxis.categories = categories;
                obj_db_LineBar_CpuMemoryUsage_Data.chart.renderTo = "oss_avgReadDiv";
                obj_db_LineBar_CpuMemoryUsage_Data.chart.width='500';
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_db_LineBar_CpuMemoryUsage_Data);
        		}
        		
                obj_db_LineBar_CpuMemoryUsage_Data.series[0].data = cpuData;
                obj_db_LineBar_CpuMemoryUsage_Data.series[1].data = memoryData;
                
                chart = new Highcharts.Chart(obj_db_LineBar_CpuMemoryUsage_Data);
        });
    }

/*****************************************************************************/
//Function for disk read and write - Area Chart
//Param - File System name, start date, end date, datafunction (average/min/max), targetkind , fetchematrics
//Return - Returns the graph plotted in container
/*****************************************************************************/
 oss_Area_ReadWrite_Data = function(fsName, sDate, endDate, dataFunction, targetKind, fetchMetrics, isZoom)
 {
	  var count = 0;
         var readData = [],categories = [], writeData = [];
        obj_db_Area_ReadWrite_Data = JSON.parse(JSON.stringify(chartConfig_Area_ReadWrite));
        $.post("/api/get_fs_stats_for_targets/",
        	{targetkind: targetKind, datafunction: dataFunction, fetchmetrics: fetchMetrics, 
            starttime: sDate, filesystem: fsName, endtime: endDate})
         .success(function(data, textStatus, jqXHR) {
            var hostName='';
            var avgMemoryApiResponse = data;
            if(avgMemoryApiResponse.success)
             {
                 var response = avgMemoryApiResponse.response;
                 $.each(response, function(resKey, resValue)
                 {
                	readData.push(resValue.stats_read_bytes/1024);
                	writeData.push(((0-resValue.stats_write_bytes)/1024));
                 	
 			        categories.push(resValue.timestamp);
		         });
              }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
    	   		obj_db_Area_ReadWrite_Data.chart.renderTo = "oss_avgWriteDiv";
    	   		obj_db_Area_ReadWrite_Data.chart.width='500';
                obj_db_Area_ReadWrite_Data.xAxis.categories = categories;
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_db_Area_ReadWrite_Data);
        		}
                
                obj_db_Area_ReadWrite_Data.series[0].data = readData;
                obj_db_Area_ReadWrite_Data.series[1].data = writeData;
                
        		chart = new Highcharts.Chart(obj_db_Area_ReadWrite_Data);
        });
}
/***********************************************************************/
 loadOSSUsageSummary = function (){
	 $('#ossSummaryTbl').html("<tr><td width='100%' align='center' height='180px'><img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' /></td></tr>");
	 var innerContent = "";
	 $.post("/api/getfilesystem/",{filesystem: $('#fsSelect').val()})
     .success(function(data, textStatus, jqXHR) {
         if(data.success)
         {
             var response = data.response;
             $.each(response, function(resKey, resValue) {
            	 innerContent = innerContent + 
            	 "<tr><td class='txtright'>MGS Hostname:</td><td class='tblContent txtleft'>"+resValue.mgsname+"</td><td>&nbsp;</td><td>&nbsp;</td></tr>"+
                 "<tr><td class='txtright'>MDS Hostname:</td><td class='tblContent txtleft'>"+resValue.mdsname+"</td><td class='txtright'>Failover Status:</td><td class='tblContent txtleft'>--</td></tr>"+
                 "<tr><td class='txtright'>File System Name:</td><td class='tblContent txtleft'>"+resValue.fsname+"</td><td>&nbsp;</td><td>&nbsp;</td></tr>"+
                 "<tr><td class='txtright'>Standby OSS Hostname:</td><td class='tblContent txtleft'>--</td><td>&nbsp;</td><td>&nbsp;</td></tr>"+
                 "<tr><td class='txtright'>Total OSTs:</td><td class='tblContent txtleft'>"+resValue.noofost+" </td><td>&nbsp;</td><td>&nbsp;</td></tr>"+
                 "<tr><td class='txtright'>OSS Status:</td>";
            	 if(resValue.status == "OK" || resValue.status == "STARTED")
            	 {
            		 innerContent = innerContent + "<td class='tblContent txtleft status_ok'>"+resValue.mdsstatus+"</td><td>&nbsp;</td><td>&nbsp;</td></tr>";
            	 }
            	 else if(resValue.status == "WARNING" || resValue.status == "RECOVERY")
            	 {
            		 innerContent = innerContent + "<td class='tblContent txtleft status_warning'>"+resValue.mdsstatus+"</td><td>&nbsp;</td><td>&nbsp;</td></tr>";
            	 }
            	 else if(resValue.status == "STOPPED")
            	 {
            		 innerContent = innerContent + "<td class='tblContent txtleft status_stopped'>"+resValue.mdsstatus+"</td><td>&nbsp;</td><td>&nbsp;</td></tr>";
            	 }
             });
         }
    })
	.error(function(event) {
	})
	.complete(function(event){
		$('#ossSummaryTbl').html(innerContent);
    });
 }