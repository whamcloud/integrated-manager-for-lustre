/*******************************************************************************/
// File name: custom_dashboard.js
// Description: Plots all the graphs for dashboard landing page.
//------------------Configuration functions--------------------------------------
// 1) chartConfig_Bar_DB	-	Bar chart configuration for space and inodes graph
// 2) chartConfig_Pie_DB	-	Pie chart configuration for space and inodes graph
// 3) chartConfig_Line_CpuUsage	-	Line chart configuration for cpu usage
// 4) chartConfig_Line_MemoryUsage	-	Line chart configuration for memory usage
// 5) chartConfig_Line_DiskRead	-	Line chart configuration for disk read
// 6) chartConfig_Line_DiskWrite	-	Line chart configuration for disk write
// 7) chartConfig_Mgs_Line_CpuUsage	-	Line chart configuration of MDS/MGS for cpu usage
// 8) chartConfig_Mgs_Line_MemoryUsage	-	Line chart configuration of MDS/MGS for memory usage
// 9) chartConfig_Mgs_Line_DiskRead	-	Line chart configuration of MDS/MGS for disk read
// 10)chartConfig_Mgs_Line_DiskWrite	-	Line chart configuration of MDS/MGS for disk write

//------------------ Data Loader functions--------------------------------------
// 1) db_Bar_Space_Data(isZoom)
// 2) db_Pie_Space_Data(isZoom)
// 3) db_Bar_INodes_Data(isZoom)
// 4) db_Pie_INodes_Data(isZoom)
// 5) db_Line_CpuUsage_Data(isZoom)
// 6) db_Line_MemoryUsage_Data(isZoom)
// 7) db_Line_DiskRead_Data(isZoom)
// 8) db_Line_DiskWrite_Data(isZoom)
// 9) db_Mgs_Line_CpuUsage_Data(isZoom)
// 10) db_Mgs_Line_MemoryUsage_Data(isZoom)
// 11) db_Mgs_Line_DiskRead_Data(isZoom)
// 12) db_Mgs_Line_DiskWrite_Data(isZoom)
/*******************************************************************************/
var chartConfig_Bar_DB = 
{			
    chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
	style:{ width:'100%',  height:'200px' },
    },
    title:{text:'', style: { fontSize: '12px' } },
    zoomType: 'xy',
    xAxis:{ categories: ['Usage'], text: '' },
    yAxis:{max:100, min:0, startOnTick:false, title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
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
/*******************************************************************************/
var chartConfig_Pie_DB = 
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
// For all file systems CPU Usage
/*********************************************************************************/
var chartConfig_Line_CpuUsage = 
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
//For all file systems Memory Usage
/*********************************************************************************/
var chartConfig_Line_MemoryUsage =
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
//For all file systems Disk Read
/*********************************************************************************/
var chartConfig_Line_DiskRead =
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
//For all file systems Disk Write
/*********************************************************************************/
var chartConfig_Line_DiskWrite =
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
var chartConfig_Mgs_Line_CpuUsage =
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
var chartConfig_Mgs_Line_MemoryUsage =
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
var chartConfig_Mgs_Line_DiskRead =
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
var chartConfig_Mgs_Line_DiskWrite =
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
// Function for space usage for all file systems	- Bar Chart
// Param - File System name, start date, end date, datafunction (average/min/max)
// Return - Returns the graph plotted in container
/*****************************************************************************/

	db_Bar_Space_Data = function(isZoom)
    {
        var free=0,used=0;
        var freeData = [],usedData = [],categories = [];
        $.post("/api/getfsdiskusage/",{endtime: "", datafunction: "", starttime: "", filesystem: ""})
	    .success(function(data, textStatus, jqXHR) 
        {   
	    	if(data.success)
		    {
		        var response = data.response;
			    var totalDiskSpace=0,totalFreeSpace=0;
			    $.each(response, function(resKey, resValue) 
		        {
		    	    totalFreeSpace = resValue.kbytesfree/1024;
				    totalDiskSpace = resValue.kbytestotal/1024;
				    free = Math.round(((totalFreeSpace/1024)/(totalDiskSpace/1024))*100);
				    used = Math.round(100 - free);
				    
			        freeData.push(free);
			        usedData.push(used);
			        
			        categories.push(resValue.filesystem);
			    });
			    
			    
		    }
        })
	    .error(function(event) 
        {
	         // Display of appropriate error message
	    })
        .complete(function(event){
			obj_db_Bar_Space_Data = chartConfig_Bar_DB;
			if(isZoom == 'true')
			{
				obj_db_Bar_Space_Data.chart.width = "780";
				obj_db_Bar_Space_Data.chart.height = "360";
				obj_db_Bar_Space_Data.chart.style.height = "360";
				obj_db_Bar_Space_Data.chart.style.width = "100%";
				obj_db_Bar_Space_Data.chart.renderTo = "dialog_container";
			}
			else
			{
				obj_db_Bar_Space_Data.chart.renderTo = "container";
			}
            obj_db_Bar_Space_Data.xAxis.categories = categories;
            obj_db_Bar_Space_Data.title.text="All File System Space Usage";
            obj_db_Bar_Space_Data.yAxis.title.text = '%';
            obj_db_Bar_Space_Data.xAxis.labels = {
                    rotation: 310,
            }
            obj_db_Bar_Space_Data.series = [
            {   
                type: 'column',
                name: 'Used Capacity',
                data: usedData
            },
            {
                type: 'column',
                name: 'Free Capacity',
                data: freeData
            }];
            chart = new Highcharts.Chart(obj_db_Bar_Space_Data);
        });
    }
/*****************************************************************************/
// Function for space usage for all file systems	- Pie Chart
// Param - File System name, start date, end date, datafunction (average/min/max)
// Return - Returns the graph plotted in container
/*****************************************************************************/
    db_Pie_Space_Data = function(isZoom)
    {
        var free=0,used=0;
        $.post("/api/getfsdiskusage/",{endtime: "", datafunction: "", starttime: "", filesystem: ""})
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
            obj_db_Pie_Space_Data = chartConfig_Pie_DB;
            obj_db_Pie_Space_Data.title.text="All File System Space Usage";
            obj_db_Pie_Space_Data.chart.renderTo = "container2";
            obj_db_Pie_Space_Data.series = [{
                type: 'pie',
                name: 'Browser share',
                data: [
                    ['Free',    free],
                    ['Used',    used]
                    ]
                }];
            chart = new Highcharts.Chart(obj_db_Pie_Space_Data);
        });
    }
/*****************************************************************************/
// Function for free INodes	- Bar Chart
// Param - File System name, start date, end date, datafunction (average/min/max)
// Return - Returns the graph plotted in container
/*****************************************************************************/
    db_Bar_INodes_Data = function(isZoom)
    {
      var free=0,used=0;
      var freeData = [],usedData = [],categories = [];
        $.post("/api/getfsinodeusage/",{endtime: "", datafunction: "", starttime: "", filesystem: ""})
        .success(function(data, textStatus, jqXHR) 
        {   
            if(data.success)
            {
                var response = data.response;
                var totalDiskSpace=0,totalFreeSpace=0;
                $.each(response, function(resKey, resValue) 
                {
                	totalFreeSpace = resValue.filesfree/1024;
				    totalDiskSpace = resValue.filestotal/1024;
				    free = Math.round(((totalFreeSpace/1024)/(totalDiskSpace/1024))*100);
				    used = Math.round(100 - free);
				    
			        freeData.push(free);
			        usedData.push(used);
			        
			        categories.push(resValue.filesystem);
                });
            }
        })
        .error(function(event) 
        {
             // Display of appropriate error message
        })
        .complete(function(event){
            obj_db_Bar_INodes_Data = chartConfig_Bar_DB;
            obj_db_Bar_INodes_Data.xAxis.categories = categories;
            obj_db_Bar_INodes_Data.title.text="Files Vs Free Nodes";
            obj_db_Bar_INodes_Data.yAxis.title.text = '%';
            obj_db_Bar_INodes_Data.chart.renderTo = "container1";
            obj_db_Bar_INodes_Data.xAxis.labels = {
                    rotation: 310,
            }
            obj_db_Bar_INodes_Data.series = [
            {   
                type: 'column',
                name: 'Used Capacity',
                data: usedData
            },
            {
                type: 'column',
                name: 'Free Capacity',
                data: freeData
            }];
            chart = new Highcharts.Chart(obj_db_Bar_INodes_Data);
        });
    }
/*****************************************************************************/
// Function for free INodes	- Pie Chart
// Param - File System name, start date, end date, datafunction (average/min/max)
// Return - Returns the graph plotted in container
/*****************************************************************************/
    db_Pie_INodes_Data = function(isZoom)
    {
        var free=0,used=0;
        $.post("/api/getfsinodeusage/",{endtime: "", datafunction: "", starttime: "", filesystem: ""})
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
           obj_db_Pie_INodes_Data = chartConfig_Pie_DB;
           obj_db_Pie_INodes_Data.title.text="Files Vs Free Nodes";
           obj_db_Pie_INodes_Data.chart.renderTo = "container3";       
           obj_db_Pie_INodes_Data.series = [{
               type: 'pie',
               name: 'Browser share',
               data: [
                  ['Free',    free],
                  ['Used',    used]
               ]
            }];
            chart = new Highcharts.Chart(obj_db_Pie_INodes_Data);
        });
     }

/*****************************************************************************/
// Function for cpu usage - Line Chart
// Param - File System name, start date, end date, datafunction (average/min/max)
// Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Line_CpuUsage_Data = function(isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
		obj_db_Line_CpuUsage_Data = chartConfig_Line_CpuUsage;
		$.post("/api/getservercpuusage/",{datafunction: "average", hostname: "", endtime: "29-20-2011", starttime: "29-20-2011"})
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
		          obj_db_Line_CpuUsage_Data.series[count] = {
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
                 obj_db_Line_CpuUsage_Data.series[count] = { name: hostName, data: optionData };
            }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_db_Line_CpuUsage_Data.xAxis.categories = categories;
                obj_db_Line_CpuUsage_Data.xAxis.title.text = 'Time (hh:mm:ss)';
                obj_db_Line_CpuUsage_Data.yAxis.title.text = 'Percentage';
                if(isZoom == 'true')
        		{
        			obj_db_Line_CpuUsage_Data.chart.width = "780";
        			obj_db_Line_CpuUsage_Data.chart.height = "360";
        			obj_db_Line_CpuUsage_Data.chart.style.height = "360";
        			obj_db_Line_CpuUsage_Data.chart.style.width = "100%";
        			obj_db_Line_CpuUsage_Data.chart.renderTo = "dg_db_cpu_usage";
        		}
        		else
        		{
        			obj_db_Line_CpuUsage_Data.chart.renderTo = "avgCPUDiv";
        		}
        		
                obj_db_Line_CpuUsage_Data.title.text="CPU Usage";
                chart = new Highcharts.Chart(obj_db_Line_CpuUsage_Data);
        });
    }

/*****************************************************************************/
//Function for memory usage - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Line_MemoryUsage_Data = function(isZoom)
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_db_Line_MemoryUsage_Data = chartConfig_Line_MemoryUsage;
        obj_db_Line_MemoryUsage_Data.chart.renderTo = "avgMemoryDiv";
        $.post("/api/getservermemoryusage/",{datafunction: "average", hostname: "", endtime: "29-20-2011", starttime: "29-20-2011"})
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
		          obj_db_Line_MemoryUsage_Data.series[count] = {
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
                 obj_db_Line_MemoryUsage_Data.series[count] = { name: hostName, data: optionData };
		      }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_db_Line_MemoryUsage_Data.xAxis.categories = categories;
                obj_db_Line_MemoryUsage_Data.xAxis.title.text = 'Time (hh:mm:ss)';
                obj_db_Line_MemoryUsage_Data.yAxis.title.text = 'GB';
                obj_db_Line_MemoryUsage_Data.title.text = "Memory Usage";
                
                chart = new Highcharts.Chart(obj_db_Line_MemoryUsage_Data);
        });
}

/*****************************************************************************/
//Function for disk read - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Line_DiskRead_Data = function(isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_db_Line_DiskRead_Data = chartConfig_Line_DiskRead;
        obj_db_Line_DiskRead_Data.title.text = "Disk Read";
        obj_db_Line_DiskRead_Data.chart.renderTo = "avgReadDiv";
        $.post("/api/gettargetreads/",{datafunction: "average", endtime: "29-20-2011", targetname: "", hostname: "", starttime: "29-20-2011"})
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
		          obj_db_Line_DiskRead_Data.series[count] = {
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
                 obj_db_Line_DiskRead_Data.series[count] = { name: targetName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_db_Line_DiskRead_Data.xAxis.categories = categories;
                obj_db_Line_DiskRead_Data.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_db_Line_DiskRead_Data);
        });
}

/*****************************************************************************/
//Function for disk write - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/

 db_Line_DiskWrite_Data = function(isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_db_Line_DiskWrite_Data = chartConfig_Line_DiskWrite;
        obj_db_Line_DiskWrite_Data.title.text = "Disk Write";
        obj_db_Line_DiskWrite_Data.chart.renderTo = "avgWriteDiv";
        $.post("/api/gettargetwrites/",{datafunction: "average", endtime: "29-20-2011", targetname: "", hostname: "", starttime: "29-20-2011"})
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
		          obj_db_Line_DiskWrite_Data.series[count] = {
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
                 obj_db_Line_DiskWrite_Data.series[count] = { name: targetName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_db_Line_DiskWrite_Data.xAxis.categories = categories;
                obj_db_Line_DiskWrite_Data.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_db_Line_DiskWrite_Data);
        });
}   

/*****************************************************************************/
//Function for cpu usage for MDS/MGS - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Mgs_Line_CpuUsage_Data = function(isZoom)
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_db_Mgs_Line_CpuUsage_Data = chartConfig_Mgs_Line_CpuUsage;
        obj_db_Mgs_Line_CpuUsage_Data.title.text="CPU Usage";
        obj_db_Mgs_Line_CpuUsage_Data.chart.renderTo = "mgsavgCPUDiv";
        $.post("/api/getservercpuusage/",{datafunction: "average", hostname: "", endtime: "29-20-2011", starttime: "29-20-2011"})
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
		          obj_db_Mgs_Line_CpuUsage_Data.series[count] = {
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
                 obj_db_Mgs_Line_CpuUsage_Data.series[count] = { name: hostName, data: optionData };
             }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_db_Mgs_Line_CpuUsage_Data.xAxis.categories = categories;
                obj_db_Mgs_Line_CpuUsage_Data.yAxis.title.text = 'Percentage';
                chart = new Highcharts.Chart(obj_db_Mgs_Line_CpuUsage_Data);
        });
    }

/*****************************************************************************/
//Function for memory usage for MDS/MGS - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Mgs_Line_MemoryUsage_Data = function(isZoom)
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_db_Mgs_Line_MemoryUsage_Data = chartConfig_Mgs_Line_MemoryUsage;
        obj_db_Mgs_Line_MemoryUsage_Data.title.text = "Memory Usage";
        obj_db_Mgs_Line_MemoryUsage_Data.chart.renderTo = "mgsavgMemoryDiv";
        $.post("/api/getservermemoryusage/",{datafunction: "average", hostname: "", endtime: "29-20-2011", starttime: "29-20-2011"})
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
		          obj_db_Mgs_Line_MemoryUsage_Data.series[count] = {
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
                 obj_db_Mgs_Line_MemoryUsage_Data.series[count] = { name: hostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_db_Mgs_Line_MemoryUsage_Data.xAxis.categories = categories;
                obj_db_Mgs_Line_MemoryUsage_Data.yAxis.title.text = 'GB';
                chart = new Highcharts.Chart(obj_db_Mgs_Line_MemoryUsage_Data);
        });
}

/*****************************************************************************/
//Function for disk read for MDS/MGS - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Mgs_Line_DiskRead_Data = function(isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_db_Mgs_Line_DiskRead_Data = chartConfig_Mgs_Line_DiskRead;
        obj_db_Mgs_Line_DiskRead_Data.title.text = "Disk Read";
        obj_db_Mgs_Line_DiskRead_Data.chart.renderTo = "mgsavgReadDiv";
        $.post("/api/gettargetreads/",{datafunction: "average", endtime: "29-20-2011", targetname: "", hostname: "", starttime: "29-20-2011"})
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
		          obj_db_Mgs_Line_DiskRead_Data.series[count] = {
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
                 obj_db_Mgs_Line_DiskRead_Data.series[count] = { name: targetName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_db_Mgs_Line_DiskRead_Data.xAxis.categories = categories;
                obj_db_Mgs_Line_DiskRead_Data.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_db_Mgs_Line_DiskRead_Data);
        });
}

 /*****************************************************************************/
//Function for disk write for MDS/MGS - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/

 db_Mgs_Line_DiskWrite_Data = function(isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_db_Mgs_Line_DiskWrite_Data = chartConfig_Mgs_Line_DiskWrite;
        obj_db_Mgs_Line_DiskWrite_Data.title.text = "Disk Write";
        obj_db_Mgs_Line_DiskWrite_Data.chart.renderTo = "mgsavgWriteDiv";
        $.post("/api/gettargetwrites/",{datafunction: "average", endtime: "29-20-2011", targetname: "", hostname: "", starttime: "29-20-2011"})
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
		          obj_db_Mgs_Line_DiskWrite_Data.series[count] = {
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
                 obj_db_Mgs_Line_DiskWrite_Data.series[count] = { name: targetName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_db_Mgs_Line_DiskWrite_Data.xAxis.categories = categories;
                obj_db_Mgs_Line_DiskWrite_Data.yAxis.title.text = 'KB';
                chart = new Highcharts.Chart(obj_db_Mgs_Line_DiskWrite_Data);
        });
}
/******************************************************************************/
// Function to show OSS/OST dashboards
/******************************************************************************/
    function showFSDashboard()
				{
	    	$("#fsSelect").change();
    }

    function showOSSDashboard()
				{
	   	 $("#ossSelect").change();
    }
/******************************************************************************/
