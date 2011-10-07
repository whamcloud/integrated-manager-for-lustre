/**************************************************************************/
//File Name - custome_oss.js
//Description - Contains function to plot pie, line and bar charts on OSS Screen
//Functions - 
//---------------------Chart Configurations function-----------------------
//	1) pieDataOptions_OSS - Pie chart configuration for Space usage.
//	2) pieDataOptions_Inode - Pie chart configuration for Inode usgae.
//	3) lineDataOptions_oss - Line Chart configuration for CPU Usage.
//	4) lineDataOptions_oss_memory - Line chart configuration for Memory Usage.
//	5) lineDataOptions_oss_disk_read - Line chart configuration for Disk Read.
//	6) lineDataOptions_oss_disk_write - Line chart configuration for Disk Write.
//---------------------Data Loaders function-------------------------------
//	1) load_OSSPagePie_disk(fsName)
//	2) load_INodePagePie_disk(fsName, sDate, eDate, dataFunction)
//	3) load_LineChart_CpuUsage_OSS(fsName, sDate, eDate, dataFunction)
//	4) load_LineChart_MemoryUsage_OSS(fsName, sDate, eDate, dataFunction)
//	5) load_LineChart_DiskRead_OSS(fsName, sDate, eDate, dataFunction
//	6) loadLineChart_DiskWrite_OSS(fsName, sDate, eDate, dataFunction)
/******************************************************************************/


//for OSS graph
var ChartConfig_Pie_Oss_Space =
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
    yAxis:{ text: '', plotLines: [{value: 0,width: 1, color: '#808080' }]},
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


//for INode graph
var ChartConfig_Pie_Oss_Inode= 
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
    yAxis:{ text: '', plotLines: [{value: 0,width: 1, color: '#808080' }]},
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

//For OSS FileSystem Avg CPU
var ChartConfig_Line_Oss_Cpu = 
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
    xAxis:{
        categories: [], 
        title:{text:''},
        labels: {
          rotation: 310,
          step: 2,
          style:{fontSize:'8px', fontWeight:'bold'}
        } 
    },
    yAxis:{max:100, min:0, startOnTick:false,title:{text:''},labels:{style:{fontSize:'8px'}}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
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

//For OSS FileSystem Memory
var ChartConfig_Line_FSMemory =
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
    xAxis:{
        categories: [], 
        title:{text:''},
        labels: {
          rotation: 310,
          step: 2,
          style:{fontSize:'8px', fontWeight:'bold'}
        } 
    },
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


//For OSS Disk Read
var ChartConfig_Line_DiskRead = 
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
    xAxis:{
        categories: [], 
        title:{text:''},
        labels: {
          rotation: 310,
          step: 2,
          style:{fontSize:'8px', fontWeight:'bold'}
        } 
    },
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


//For OSS Disk Write
var ChartConfig_Line_DiskWrite = 
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
    xAxis:{
        categories: [], 
        title:{text:''},
        labels: {
          rotation: 310,
          step: 2,
          style:{fontSize:'8px', fontWeight:'bold'}
        } 
    },
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
// Function for OSS for disk usage for
// Param - File System Name
// Return - Returns the graph plotted in container
/*****************************************************************************/
OSS_Pie_space_data = function(fsName)
{
        var free=0,used=0;
		obj_oss_pie_space = ChartConfig_Pie_Oss_Space;
        obj_oss_pie_space.title.text= fsName + " Space Usage";
        obj_oss_pie_space.chart.renderTo = "oss_container2";		
        $.post("/api/getfsdiskusage/",{endtime: "", datafunction: "", starttime: "", filesystem: fsName})
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
		.complete(function(event) {
	    obj_oss_pie_space.series = [{
				type: 'pie',
				name: 'Browser share',
				data: [
					['Free',    free],
					['Used',    used]
					]
				}];
		        chart = new Highcharts.Chart(obj_oss_pie_space);
		});
}
/*****************************************************************************/
// Function for inode usage for file name
// Param - File System name, start date, end date, datafunction (avergae/"")
// Return - Returns the graph plotted in container
/*****************************************************************************/
OSS_Pie_inode_data = function(fsName, sDate, eDate, dataFunction) //212
{
        var free=0,used=0;
		obj_oss_pie_inode = ChartConfig_Pie_Oss_Inode;
        obj_oss_pie_inode.title.text= fsName + " - Files vs Free Inodes";
        obj_oss_pie_inode.chart.renderTo = "oss_container3";		
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
		.complete(function(event) {
	    obj_oss_pie_inode.series = [{
				type: 'pie',
				name: 'Browser share',
				data: [
					['Free',    free],
					['Used',    used]
					]
				}];
		        chart = new Highcharts.Chart(obj_oss_pie_inode);
		});
}
/*****************************************************************************/
// Function for inode usage for file name
// Param - File System name, start date, end date, datafunction (avergae/"")
// Return - Returns the graph plotted in container
/*****************************************************************************/
OSS_Line_Cpu_data = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
		var seriesUpdated = 0;
        var optionData = [],categories = [];
        obj_oss_line_cpu = ChartConfig_Line_Oss_Cpu;
        obj_oss_line_cpu.title.text="CPU Usage";
        obj_oss_line_cpu.chart.renderTo = "oss_avgCPUDiv";
        $.post("/api/getservercpuusage/",{datafunction: dataFunction, hostname: fsName, endtime: sDate, starttime: eDate})
         .success(function(data, textStatus, jqXHR) {
            var ossName='';
            var avgCPUApiResponse = data;
            if(avgCPUApiResponse.success)
             {
                 var response = avgCPUApiResponse.response;
                 $.each(response, function(resKey, resValue) 
                {
          if (ossName != resValue.hostname && ossName !='')
          {
			  seriesUpdated = 1;
          obj_oss_line_cpu.series[count] = {
                name: ossName,
                data: optionData
                   };
		
          optionData = [];
          categories = [];
          count++;
          ossName = resValue.hostname;
          optionData.push(resValue.cpu);
          categories.push(resValue.timestamp);
          }
           else
           {
            ossName = resValue.hostname;
            optionData.push(resValue.cpu);
            categories.push(resValue.timestamp);
           }
		   if(seriesUpdated == 0)
		   {
			   obj_oss_line_cpu.series[0] = {
                name: ossName,
                data: optionData
                   };
		   }
		   else
		   {
			   obj_oss_line_cpu.series[count] = {
                name: ossName,
                data: optionData
                   };
		   }
          });
        }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_oss_line_cpu.xAxis.categories = categories;   
		chart = new Highcharts.Chart(obj_oss_line_cpu);
        });
    }
	
/*****************************************************************************/
// Function for Line chart memory usage
// Param - File System name, start date, end date, datafunction (avergae/"")
// Return - Returns the graph plotted in container
/*****************************************************************************/	
OSS_Line_Memory_Data = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
		var seriesUpdated = 0;
         var optionData = [],categories = [];
        obj_oss_line_memory = ChartConfig_Line_FSMemory;
        obj_oss_line_memory.title.text = "Memory Usage";
        obj_oss_line_memory.chart.renderTo = "oss_avgMemoryDiv";
        $.post("/api/getservermemoryusage/",{datafunction: dataFunction, hostname: fsName, endtime: eDate, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var ossName='';
            var avgMemoryApiResponse = data;
            if(avgMemoryApiResponse.success)
             {
                 var response = avgMemoryApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
          if (ossName != resValue.hostname && ossName !='')
          {
          obj_oss_line_memory.series[count] = {
                name: ossName,
                data: optionData
                   };
          optionData = [];
          categories = [];
		  seriesUpdated = 1;
          count++;
          ossName = resValue.hostname;
          optionData.push(resValue.memory);
          categories.push(resValue.timestamp);
          }
           else
           {
            ossName = resValue.hostname;
            optionData.push(resValue.memory);
            categories.push(resValue.timestamp);
           }
		   if(seriesUpdated == 0)
		   {
			   obj_oss_line_memory.series[0] = {
                name: ossName,
                data: optionData
                   };
		   }
		   else
		   {
			   obj_oss_line_memory.series[count] = {
                name: ossName,
                data: optionData
                   };
		   }
          });
        }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_oss_line_memory.xAxis.categories = categories;
                obj_oss_line_memory.yAxis.title.text = 'GB';
                chart = new Highcharts.Chart(obj_oss_line_memory);
        });
}


/*****************************************************************************/
// Function for Line chart Disk read
// Param - File System name, start date, end date, datafunction (avergae/"")
// Return - Returns the graph plotted in container
/*****************************************************************************/	
OSS_Line_DiskRead_Data = function(fsName, sDate, eDate, dataFunction) //221
 {
        var count = 0;
        var optionData = [],categories = [];
		var seriesUpdated = 0;
        obj_oss_line_diskread = ChartConfig_Line_DiskRead;
        obj_oss_line_diskread.title.text = "Disk Read";
        obj_oss_line_diskread.chart.renderTo = "oss_avgReadDiv";
        $.post("/api/gettargetreads/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var ossName='';
            var avgDiskReadApiResponse = data;
            if(avgDiskReadApiResponse.success)
             {
                 var response = avgDiskReadApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
          if (ossName != resValue.targetname && ossName !='')
          {
          obj_oss_line_diskread.series[count] = {
                name: ossName,
                data: optionData
                   };
          optionData = [];
          categories = [];
		  seriesUpdated = 1;
          count++;
          ossName = resValue.targetname;
          optionData.push(resValue.reads);
          categories.push(resValue.timestamp);
          }
           else
           {
            ossName = resValue.targetname;
            optionData.push(resValue.reads);
            categories.push(resValue.timestamp);
           }
		   if(seriesUpdated == 0)
		   {
			   obj_oss_line_diskread.series[0] = {
                name: ossName,
                data: optionData
                   };
		   }
		   else
		   {
			   obj_oss_line_diskread.series[count] = {
                name: ossName,
                data: optionData
                   };
		   }
          });
        }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_oss_line_diskread.xAxis.categories = categories;
                obj_oss_line_diskread.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_oss_line_diskread);
        });
}

/*****************************************************************************/
// Function for Disk Write
// Param - File System name, start date, end date, datafunction (avergae/"")
// Return - Returns the graph plotted in container
/*****************************************************************************/	
OSS_Line_DiskWrite_Data = function(fsName, sDate, eDate, dataFunction) //224
 {
        var count = 0;
        var optionData = [],categories = [];
		var seriesUpdated = 0;
        obj_oss_line_diskwrite = ChartConfig_Line_DiskWrite;
        obj_oss_line_diskwrite.title.text = "Disk Write";
        obj_oss_line_diskwrite.chart.renderTo = "oss_avgWriteDiv";
        $.post("/api/gettargetwrites/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
         .success(function(data, textStatus, jqXHR) {
            var ossName='';
            var avgDiskWriteApiResponse = data;
            if(avgDiskWriteApiResponse.success)
             {
                 var response = avgDiskWriteApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
          if (ossName != resValue.targetname && ossName !='')
          {
          obj_oss_line_diskwrite.series[count] = {
                name: ossName,
                data: optionData
                   };
          optionData = [];
          categories = [];
		  seriesUpdated = 1;
          count++;
          ossName = resValue.targetname;
          optionData.push(resValue.writes);
          categories.push(resValue.timestamp);
          }
           else
           {
            ossName = resValue.targetname;
            optionData.push(resValue.writes);
            categories.push(resValue.timestamp);
           }
		   if(seriesUpdated == 0)
		   {
			   obj_oss_line_diskwrite.series[0] = {
                name: ossName,
                data: optionData
                   };
		   }
		   else
		   {
			   obj_oss_line_diskwrite.series[count] = {
                name: ossName,
                data: optionData
                   };
		   }
          });
        }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_oss_line_diskwrite.xAxis.categories = categories;
                obj_oss_line_diskwrite.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_oss_line_diskwrite);
        });
}   