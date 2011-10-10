/*******************************************************************************/
// File name: custom_dashboard.js
// Description: Plots all the graphs for file system dashboard

//------------------Configuration functions--------------------------------------
// 1) chartConfig_fs_Pie_DB	-	Pie chart configuration for space and inodes graph
// 2) chartConfig_fs_Line_CpuUsage	-	Line chart configuration for cpu usage
// 3) chartConfig_fsLine_MemoryUsage	-	Line chart configuration for memory usage
// 4) chartConfig_fs_Line_DiskRead	-	Line chart configuration for disk read
// 5) chartConfig_fs_Line_DiskWrite	-	Line chart configuration for disk write
// 6) chartConfig_fs_Mgs_Line_CpuUsage	-	Line chart configuration of MDS/MGS for cpu usage
// 7) chartConfig_fs_Mgs_Line_MemoryUsage	-	Line chart configuration of MDS/MGS for memory usage
// 8) chartConfig_fs_Mgs_Line_DiskRead	-	Line chart configuration of MDS/MGS for disk read
// 9) chartConfig_fs_Mgs_Line_DiskWrite	-	Line chart configuration of MDS/MGS for disk write

//------------------ Data Loader functions--------------------------------------
// 1) fs_Pie_Space_Data(fsName, sDate, eDate, dataFunction)
// 2) fs_Pie_INodes_Data(fsName, sDate, eDate, dataFunction)
// 3) fs_Line_CpuUsage_Data(fsName, sDate, eDate, dataFunction, isZoom)
// 4) fs_Line_MemoryUsage_Data(fsName, sDate, eDate, dataFunction, isZoom)
// 5) fs_Line_DiskRead_Data(fsName, sDate, eDate, dataFunction, isZoom)
// 6) fs_Line_DiskWrite_Data(fsName, sDate, eDate, dataFunction, isZoom)
// 7) fs_Mgs_Line_CpuUsage_Data(fsName, sDate, eDate, dataFunction, isZoom)
// 8) fs_Mgs_Line_MemoryUsage_Data(fsName, sDate, eDate, dataFunction, isZoom)
// 9) fs_Mgs_Line_DiskRead_Data(fsName, sDate, eDate, dataFunction, isZoom)
// 10) fs_Mgs_Line_DiskWrite_Data(fsName, sDate, eDate, dataFunction, isZoom)
/*******************************************************************************/
//Pie chart configuration 
/*******************************************************************************/
var chartConfig_fs_Pie_DB = 
{
    chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
	style:{ width:'100%',  height:'200px' },
    },
    title:{ text: '', style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
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
	     pie:{allowPointSelect: true,cursor: 'pointer',showInLegend: true,size: '100%',dataLabels:{enabled: false,color: '#000000',connectorColor: '#000000'}}
	 },
	 series: []
};
/*********************************************************************************/	
// For file systems CPU Usage
/*********************************************************************************/
var chartConfig_fs_Line_CpuUsage = 
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{categories: [],title:{text:''},labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}},
    yAxis:{max:100, min:0, startOnTick:false, title:{text:''},labels:{style:{fontSize:'8px'}}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
    plotOptions:{series:{marker: {enabled: false}} },
    credits:{ enabled:false },
    tooltip:
    {
	    formatter: function() 
        {
	        return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	series: []
};

/*********************************************************************************/	
//For file systems Memory Usage
/*********************************************************************************/
var chartConfig_fsLine_MemoryUsage =
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{categories: [],title:{text:''},labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}},
    yAxis:{title:{text:''},labels:{style:{fontSize:'8px'}}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
    plotOptions:{series:{marker: {enabled: false}} },
    credits:{ enabled:false },
    tooltip:
    {
	    formatter: function() 
        {
	        return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	series: []
};
/*********************************************************************************/	
//For file systems Disk Read
/*********************************************************************************/
var chartConfig_fs_Line_DiskRead =
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{categories: [],title:{text:''},labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}},
    yAxis:{title:{text:''},labels:{style:{fontSize:'8px'}}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
    plotOptions:{series:{marker: {enabled: false}} },
    credits:{ enabled:false },
    tooltip:
    {
	    formatter: function() 
        {
	        return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	series: []
};
/*********************************************************************************/	
//For file systems Disk Write
/*********************************************************************************/
var chartConfig_fs_Line_DiskWrite =
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{categories: [],title:{text:''},labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}},
    yAxis:{title:{text:''},labels:{style:{fontSize:'8px'}}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
    plotOptions:{series:{marker: {enabled: false}} },
    credits:{ enabled:false },
    tooltip:
    {
	    formatter: function() 
        {
	        return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	series: []
};
/*********************************************************************************/	
// All MDS/MGS CPU Usage
/*********************************************************************************/
var chartConfig_fs_Mgs_Line_CpuUsage =
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{categories: [],title:{text:''},labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}},
    yAxis:{max:100, min:0, startOnTick:false, title:{text:''},labels:{style:{fontSize:'8px'}}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
    plotOptions:{series:{marker: {enabled: false}} },
    credits:{ enabled:false },
    tooltip:
    {
	    formatter: function() 
        {
	        return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	series: []
};
/*********************************************************************************/	
//All MDS/MGS Memory Usage
/*********************************************************************************/
var chartConfig_fs_Mgs_Line_MemoryUsage =
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{categories: [],title:{text:''},labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}},
    yAxis:{title:{text:''},labels:{style:{fontSize:'8px'}}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
    plotOptions:{series:{marker: {enabled: false}} },
    credits:{ enabled:false },
    tooltip:
    {
	    formatter: function() 
        {
	        return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	series: []
};
/*********************************************************************************/	
//All MDS/MGS Disk Read
/*********************************************************************************/
var chartConfig_fs_Mgs_Line_DiskRead =
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{categories: [],title:{text:''},labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}},
    yAxis:{title:{text:''},labels:{style:{fontSize:'8px'}}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
    plotOptions:{series:{marker: {enabled: false}} },
    credits:{ enabled:false },
    tooltip:
    {
	    formatter: function() 
        {
	        return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	series: []
};
/*********************************************************************************/	
//All MDS/MGS Disk Write
/*********************************************************************************/
var chartConfig_fs_Mgs_Line_DiskWrite =
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{categories: [],title:{text:''},labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}},
    yAxis:{title:{text:''},labels:{style:{fontSize:'8px'}}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{enabled:false, layout: 'vertical', align: 'right', verticalAlign: 'top', x: 0, y: 10, borderWidth: 0},
    plotOptions:{series:{marker: {enabled: false}} },
    credits:{ enabled:false },
    tooltip:
    {
	    formatter: function() 
        {
	        return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	series: []
};
/*****************************************************************************/
//Function for space usage for selected file systems - Pie Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
	fs_Pie_Space_Data = function(fsName, sDate, eDate, dataFunction)
    {
        var free=0,used=0;
        $.post("/api/getfsdiskusage/",{endtime: eDate, datafunction: dataFunction, starttime: sDate, filesystem: fsName})
        .success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
                var totalDiskSpace=0,totalFreeSpace=0;
                $.each(response, function(resKey, resValue)
                {
                    totalFreeSpace = totalFreeSpace + resValue.kbytesfree/1024;
                    totalDiskSpace = totalDiskSpace + resValue.kbytestotal/1024;
                });
                free = Math.round(((totalFreeSpace/1024)/(totalDiskSpace/1024))*100);
                used = Math.round(100 - free);
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
        .complete(function(event){
            obj_fs_Pie_Space_Data = chartConfig_fs_Pie_DB;
            obj_fs_Pie_Space_Data.title.text="All File System Space Usage";
            obj_fs_Pie_Space_Data.chart.renderTo = "fs_container2";
            obj_fs_Pie_Space_Data.series = [{
                type: 'pie',
                name: 'Browser share',
                data: [
                    ['Free',    free],
                    ['Used',    used]
                    ]
                }];
            chart = new Highcharts.Chart(obj_fs_Pie_Space_Data);
        });
    }
/*****************************************************************************/
//Function for free inodes for selected file systems - Pie Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
	fs_Pie_INodes_Data = function(fsName, sDate, eDate, dataFunction)
    {
        var free=0,used=0;
        $.post("/api/getfsinodeusage/",{endtime: eDate, datafunction: dataFunction, starttime: sDate, filesystem: fsName})
        .success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
                var totalDiskSpace=0,totalFreeSpace=0;
                $.each(response, function(resKey, resValue)
                {
                    totalFreeSpace = totalFreeSpace + resValue.filesfree/1024;
                    totalDiskSpace = totalDiskSpace + resValue.filestotal/1024;
                });
                free = Math.round(((totalFreeSpace/1024)/(totalDiskSpace/1024))*100);
                used = Math.round(100 - free);
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
        .complete(function(event)
        {
           obj_fs_Pie_INodes_Data = chartConfig_fs_Pie_DB;
           obj_fs_Pie_INodes_Data.title.text="Files Vs Free Nodes";
           obj_fs_Pie_INodes_Data.chart.renderTo = "fs_container3";       
           obj_fs_Pie_INodes_Data.series = [{
               type: 'pie',
               name: 'Browser share',
               data: [
                  ['Free',    free],
                  ['Used',    used]
               ]
            }];
            chart = new Highcharts.Chart(obj_fs_Pie_INodes_Data);
        });
     }

/*****************************************************************************/
//Function for cpu usage for selected file systems - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max), isZoom
//Return - Returns the graph plotted in container
/*****************************************************************************/
 fs_Line_CpuUsage_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_Line_CpuUsage_Data = chartConfig_fs_Line_CpuUsage;
        obj_fs_Line_CpuUsage_Data.title.text="CPU Usage";
        obj_fs_Line_CpuUsage_Data.chart.renderTo = "fs_avgCPUDiv";
        $.post("/api/getservercpuusage/",{datafunction: dataFunction, hostname: "", endtime: eDate, starttime: sDate})
         .success(function(data, textStatus, jqXHR) 
          {
            var hostName='';
            var avgCPUApiResponse = data;
            if(avgCPUApiResponse.success)
            {
                 var response = avgCPUApiResponse.response;
                 $.each(response, function(resKey, resValue) 
                {
		          if (hostName != resValue.hostname && hostName !='')
		          {
		          obj_fs_Line_CpuUsage_Data.series[count] = {
		                name: hostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          hostName = resValue.hostname;
		          optionData.push(resValue.cpu);
		          categories.push(resValue.timestamp);
			       }
			       else
			       {
			        hostName = resValue.hostname;
			        optionData.push(resValue.cpu);
			        categories.push(resValue.timestamp);
			       }
			     });
                 obj_fs_Line_CpuUsage_Data.series[count] = { name: hostName, data: optionData };
            }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_Line_CpuUsage_Data.xAxis.categories = categories;
                obj_fs_Line_CpuUsage_Data.yAxis.title.text = 'Percentage';
                chart = new Highcharts.Chart(obj_fs_Line_CpuUsage_Data);
        });
    }

/*****************************************************************************/
//Function for memory usage for selected file systems - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max), isZoom
//Return - Returns the graph plotted in container
/*****************************************************************************/
 fs_Line_MemoryUsage_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_fs_Line_MemoryUsage_Data = chartConfig_fsLine_MemoryUsage;
        obj_fs_Line_MemoryUsage_Data.title.text = "Memory Usage";
        obj_fs_Line_MemoryUsage_Data.chart.renderTo = "fs_avgMemoryDiv";
        $.post("/api/getservermemoryusage/",{datafunction: dataFunction, hostname: "", endtime: eDate, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var hostName='';
            var avgMemoryApiResponse = data;
            if(avgMemoryApiResponse.success)
             {
                 var response = avgMemoryApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (hostName != resValue.hostname && hostName !='')
		          {
		          obj_fs_Line_MemoryUsage_Data.series[count] = {
		                name: hostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          hostName = resValue.hostname;
		          optionData.push(resValue.memory);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            hostName = resValue.hostname;
		            optionData.push(resValue.memory);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_fs_Line_MemoryUsage_Data.series[count] = { name: hostName, data: optionData };
		      }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_Line_MemoryUsage_Data.xAxis.categories = categories;
                obj_fs_Line_MemoryUsage_Data.yAxis.title.text = 'GB';
                chart = new Highcharts.Chart(obj_fs_Line_MemoryUsage_Data);
        });
}

/*****************************************************************************/
//Function for disk read for selected file systems - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max), isZoom
//Return - Returns the graph plotted in container
/*****************************************************************************/
 fs_Line_DiskRead_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_Line_DiskRead_Data = chartConfig_fs_Line_DiskRead;
        obj_fs_Line_DiskRead_Data.title.text = "Disk Read";
        obj_fs_Line_DiskRead_Data.chart.renderTo = "fs_avgReadDiv";
        $.post("/api/gettargetreads/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var targetName='';
            var avgDiskReadApiResponse = data;
            if(avgDiskReadApiResponse.success)
             {
                 var response = avgDiskReadApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (targetName != resValue.targetname && targetName !='')
		          {
		          obj_fs_Line_DiskRead_Data.series[count] = {
		                name: targetName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          targetName = resValue.targetname;
		          optionData.push(resValue.reads);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            targetName = resValue.targetname;
		            optionData.push(resValue.reads);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_fs_Line_DiskRead_Data.series[count] = { name: targetName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_Line_DiskRead_Data.xAxis.categories = categories;
                obj_fs_Line_DiskRead_Data.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_fs_Line_DiskRead_Data);
        });
}

/*****************************************************************************/
//Function for disk write for selected file systems - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max), isZoom
//Return - Returns the graph plotted in container
/*****************************************************************************/

 fs_Line_DiskWrite_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_Line_DiskWrite_Data = chartConfig_fs_Line_DiskWrite;
        obj_fs_Line_DiskWrite_Data.title.text = "Disk Write";
        obj_fs_Line_DiskWrite_Data.chart.renderTo = "fs_avgWriteDiv";
        $.post("/api/gettargetwrites/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var targetName='';
            var avgDiskWriteApiResponse = data;
            if(avgDiskWriteApiResponse.success)
             {
                 var response = avgDiskWriteApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (targetName != resValue.targetname && targetName !='')
		          {
		          obj_fs_Line_DiskWrite_Data.series[count] = {
		                name: targetName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          targetName = resValue.targetname;
		          optionData.push(resValue.writes);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            targetName = resValue.targetname;
		            optionData.push(resValue.writes);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_fs_Line_DiskWrite_Data.series[count] = { name: targetName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_Line_DiskWrite_Data.xAxis.categories = categories;
                obj_fs_Line_DiskWrite_Data.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_fs_Line_DiskWrite_Data);
        });
}   

/*****************************************************************************/
//Function for cpu usage for all MDS/MGS of selected file systems - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max), isZoom
//Return - Returns the graph plotted in container
/*****************************************************************************/
 fs_Mgs_Line_CpuUsage_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_fs_Mgs_Line_CpuUsage_Data = chartConfig_fs_Mgs_Line_CpuUsage;
        obj_fs_Mgs_Line_CpuUsage_Data.title.text="CPU Usage";
        obj_fs_Mgs_Line_CpuUsage_Data.chart.renderTo = "fs_mgsavgCPUDiv";
        $.post("/api/getservercpuusage/",{datafunction: dataFunction, hostname: "", endtime: eDate, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var hostName='';
            var avgCPUApiResponse = data;
            if(avgCPUApiResponse.success)
             {
                 var response = avgCPUApiResponse.response;
                 $.each(response, function(resKey, resValue) 
                {
		          if (hostName != resValue.hostname && hostName !='')
		          {
		          obj_fs_Mgs_Line_CpuUsage_Data.series[count] = {
		                name: hostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          hostName = resValue.hostname;
		          optionData.push(resValue.cpu);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            hostName = resValue.hostname;
		            optionData.push(resValue.cpu);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_fs_Mgs_Line_CpuUsage_Data.series[count] = { name: hostName, data: optionData };
             }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_Mgs_Line_CpuUsage_Data.xAxis.categories = categories;
                obj_fs_Mgs_Line_CpuUsage_Data.yAxis.title.text = 'Percentage';
                chart = new Highcharts.Chart(obj_fs_Mgs_Line_CpuUsage_Data);
        });
    }

 /*****************************************************************************/
//Function for memory usage for all MDS/MGS of selected file systems - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max), isZoom
//Return - Returns the graph plotted in container
/*****************************************************************************/
 fs_Mgs_Line_MemoryUsage_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_fs_Mgs_Line_MemoryUsage_Data = chartConfig_fs_Mgs_Line_MemoryUsage;
        obj_fs_Mgs_Line_MemoryUsage_Data.title.text = "Memory Usage";
        obj_fs_Mgs_Line_MemoryUsage_Data.chart.renderTo = "fs_mgsavgMemoryDiv";
        $.post("/api/getservermemoryusage/",{datafunction: dataFunction, hostname: "", endtime: eDate, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var hostName='';
            var avgMemoryApiResponse = data;
            if(avgMemoryApiResponse.success)
             {
                 var response = avgMemoryApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (hostName != resValue.hostname && hostName !='')
		          {
		          obj_fs_Mgs_Line_MemoryUsage_Data.series[count] = {
		                name: hostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          hostName = resValue.hostname;
		          optionData.push(resValue.memory);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            hostName = resValue.hostname;
		            optionData.push(resValue.memory);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_fs_Mgs_Line_MemoryUsage_Data.series[count] = { name: hostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_Mgs_Line_MemoryUsage_Data.xAxis.categories = categories;
                obj_fs_Mgs_Line_MemoryUsage_Data.yAxis.title.text = 'GB';
                chart = new Highcharts.Chart(obj_fs_Mgs_Line_MemoryUsage_Data);
        });
}

/*****************************************************************************/
//Function for disk read for all MDS/MGS of selected file systems - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max), isZoom
//Return - Returns the graph plotted in container
/*****************************************************************************/
 fs_Mgs_Line_DiskRead_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_Mgs_Line_DiskRead_Data = chartConfig_fs_Mgs_Line_DiskRead;
        obj_fs_Mgs_Line_DiskRead_Data.title.text = "Disk Read";
        obj_fs_Mgs_Line_DiskRead_Data.chart.renderTo = "fs_mgsavgReadDiv";
        $.post("/api/gettargetreads/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var targetName='';
            var avgDiskReadApiResponse = data;
            if(avgDiskReadApiResponse.success)
             {
                 var response = avgDiskReadApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (targetName != resValue.targetname && targetName !='')
		          {
		          obj_fs_Mgs_Line_DiskRead_Data.series[count] = {
		                name: targetName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          targetName = resValue.targetname;
		          optionData.push(resValue.reads);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            targetName = resValue.targetname;
		            optionData.push(resValue.reads);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_fs_Mgs_Line_DiskRead_Data.series[count] = { name: targetName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_Mgs_Line_DiskRead_Data.xAxis.categories = categories;
                obj_fs_Mgs_Line_DiskRead_Data.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_fs_Mgs_Line_DiskRead_Data);
        });
}

/*****************************************************************************/
//Function for disk write for all MDS/MGS of selected file systems - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max), isZoom
//Return - Returns the graph plotted in container
/*****************************************************************************/

 fs_Mgs_Line_DiskWrite_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_Mgs_Line_DiskWrite_Data = chartConfig_fs_Mgs_Line_DiskWrite;
        obj_fs_Mgs_Line_DiskWrite_Data.title.text = "Disk Write";
        obj_fs_Mgs_Line_DiskWrite_Data.chart.renderTo = "fs_mgsavgWriteDiv";
        $.post("/api/gettargetwrites/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var targetName='';
            var avgDiskWriteApiResponse = data;
            if(avgDiskWriteApiResponse.success)
             {
                 var response = avgDiskWriteApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (targetName != resValue.targetname && targetName !='')
		          {
		          obj_fs_Mgs_Line_DiskWrite_Data.series[count] = {
		                name: targetName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          targetName = resValue.targetname;
		          optionData.push(resValue.writes);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            targetName = resValue.targetname;
		            optionData.push(resValue.writes);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_fs_Mgs_Line_DiskWrite_Data.series[count] = { name: targetName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_Mgs_Line_DiskWrite_Data.xAxis.categories = categories;
                obj_fs_Mgs_Line_DiskWrite_Data.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_fs_Mgs_Line_DiskWrite_Data);
        });
}
/********************************************************************************/