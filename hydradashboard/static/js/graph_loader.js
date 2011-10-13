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
    marginBottom: 35,
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
    marginBottom: 35,
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
    marginBottom: 35,
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
    marginBottom: 35,
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
    marginBottom: 35,
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
    marginBottom: 35,
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
    marginBottom: 35,
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
    marginBottom: 35,
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
		chart = new Highcharts.Chart({
		      chart: {
		         renderTo: 'container',
		         defaultSeriesType: 'column',
		         marginLeft: '50',
		     	 width: '250',
		         height: '200',
		     	 style:{ width:'100%',  height:'210', position: 'inherit' },
		         marginRight: 0,
		         marginBottom: 35,
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
		      title: {
		         text: 'Free space',
		         style: { fontSize: '12px' },
		      },
		      xAxis: {
		         categories: ['ddnfs01', 'hulkfs01', 'matrixfs', 'sobofs01', 'punefs01'],
		      	labels: {rotation: 310,style:{fontSize:'8px', fontWeight:'bold'}}
		      },
		      yAxis: {
		         min: 0,
		         max:100,
		         startOnTick:false, 
		         title: {
		            text: 'Percentage'
		         },
		         /*stackLabels: {
		            enabled: true,
		            style: {
		               fontWeight: 'bold',
		               color: (Highcharts.theme && Highcharts.theme.textColor) || 'gray'
		            }
		         }*/
		      },
		      legend: {
		    	 enabled:false,
		         align: 'right',
		         x: -100,
		         verticalAlign: 'top',
		         y: 20,
		         floating: true,
		         backgroundColor: (Highcharts.theme && Highcharts.theme.legendBackgroundColorSolid) || 'white',
		         borderColor: '#CCC',
		         borderWidth: 1,
		         shadow: false
		      },
		      credits:{ enabled:false },
		      tooltip: {
		         formatter: function() {
		            return '<b>'+ this.x +'</b><br/>'+
		                this.series.name +': '+ this.y +'<br/>'+
		                'Total: '+ this.point.stackTotal;
		         }
		      },
		      plotOptions: {
		         column: {
		            stacking: 'normal',
		            /*dataLabels: {
		               enabled: true,
		               color: (Highcharts.theme && Highcharts.theme.dataLabelsColor) || 'white'
		            }*/
		         }
		      },
		       series: [{
		           data: [20, 30, 70, 40, 20],
		           stack: 0
		       }, {
		           data: [80, 70, 30, 60, 80],
		           stack: 0},
		       // second stack
		       {
		           data: [70, 80, 60, 60, 70],
		           stack: 1
		       }, {
		           data: [30, 20, 40, 40, 30],
		           stack: 1
		       }]
		   });
        /*var free=0,used=0;
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
			obj_db_Bar_Space_Data.chart.renderTo = "container";
			obj_db_Bar_Space_Data.xAxis.categories = categories;
            obj_db_Bar_Space_Data.title.text="All File System Space Usage";
            obj_db_Bar_Space_Data.yAxis.title.text = 'Percentage';
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
        });*/
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
      /*var free=0,used=0;
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
            obj_db_Bar_INodes_Data.yAxis.title.text = 'Percentage';
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
        });*/
    }
/*****************************************************************************/
// Function for free INodes	- Pie Chart
// Param - File System name, start date, end date, datafunction (average/min/max)
// Return - Returns the graph plotted in container
/*****************************************************************************/
    db_Pie_INodes_Data = function(isZoom)
    {
    	chart = new Highcharts.Chart({
		      chart: {
		    	  renderTo: 'container3',
			    	marginLeft: '50',
	        		width: '250',
	        	    height: '200',
	        		style:{ width:'100%',  height:'210', position: 'inherit' },
	        	    marginBottom: 35,
	        	    zoomType: 'xy'
		      },
		      title: {
		         text: 'Client count',
		         style: { fontSize: '12px' },
		      },
		      xAxis: {
		         categories: ['fs1', 'fs2', 'fs3', 'fs4', 'fs5'],
		         labels: {style:{fontSize:'10px', fontWeight:'bold'}}
		      },
		      yAxis: {
		         title: {
		            text: 'Number of Users'
		         },
		         plotLines: [{
		            value: 0,
		            width: 1,
		            color: '#808080'
		         }]
		      },
		      tooltip: {
		         formatter: function() {
		                   return this.x +': '+ this.y +'';
		         }
		      },
		      legend: {
		    	  enabled: false,
		         layout: 'vertical',
		         align: 'right',
		         verticalAlign: 'top',
		         x: -10,
		         y: 100,
		         borderWidth: 0
		      },
		      credits:{ enabled:false },
		      series: [{
		         name: '',
		         data: [20, 22, 25, 21, 18]
		      }]
		   });
       /* var free=0,used=0;
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
        });*/
     }

/*****************************************************************************/
// Function for cpu usage - Line Chart
// Param - File System name, start date, end date, datafunction (average/min/max)
// Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Line_CpuUsage_Data = function(isZoom)
 {
	 var chart = new Highcharts.Chart({
		    chart: {
		        renderTo: 'avgCPUDiv',
		    	marginLeft: '50',
     		width: '250',
     	    height: '200',
     		style:{ width:'100%',  height:'210', position: 'inherit' },
     	    marginBottom: 35,
     	    zoomType: 'xy'
			},
			
		    title: {
		         text: 'Server CPU and Memory',
		         style: { fontSize: '12px' },
		    },
		    xAxis: {
		        categories: ['01:35:00', '01:35:10', '01:35:20', '01:35:30', '01:35:40', '01:35:50', '01:35:60', '01:35:70', '01:35:80', '01:35:90'],
		        labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}
		    },
		    yAxis: [{
		        title: {
		            text: 'KB'
		        },
		        opposite: true,
		    },{
		        title: {
		            text: 'Percentage'
		        },
		        
		        max:100, min:0, startOnTick:false,  tickInterval: 20
		    }],
		    legend: {
		    	 enabled:false,
		    },
		    credits:{ enabled:false },
		    plotOptions:{series:{marker: {enabled: true}} },
		    series: [{
		        type: 'column',
		        data: [60, 80, 75, 72, 50, 30, 32, 35, 35, 35],
		        name: 'KB',
		        yAxis: 1
		    },{
		        type: 'line',
		        data: [20, 30, 40, 30, 33, 35, 36, 25, 25, 25],
		        name: 'Percentage',
		    }]
		});
       /* var count = 0;
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
                	renderZoomDialog(obj_db_Line_CpuUsage_Data);
        		}
        		else
        		{
        			obj_db_Line_CpuUsage_Data.chart.renderTo = "avgCPUDiv";
        		}
        		
                obj_db_Line_CpuUsage_Data.title.text="CPU Usage";
                chart = new Highcharts.Chart(obj_db_Line_CpuUsage_Data);
        });*/
    }

/*****************************************************************************/
//Function for memory usage - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Line_MemoryUsage_Data = function(isZoom)
 {
	 chart = new Highcharts.Chart({
	      chart: {
	         renderTo: 'avgMemoryDiv',
	         defaultSeriesType: 'area',
	         marginLeft: '50',
	     	 width: '250',
	         height: '200',
	     	 style:{ width:'100%',  height:'210', position: 'inherit' },
	         marginRight: 0,
	         marginBottom: 35,
	         zoomType: 'xy'
	      },
	      colors: [
			     	'#628EC5', 
			     	'#AE91D0', 
			     	'#A6C56D', 
			     	'#C76560', 
			     	'#3D96AE', 
			     	'#DB843D', 
			     	'#92A8CD', 
			     	'#A47D7C', 
			     	'#B5CA92'
			     ],
	      title: {
	         text: 'Read Vs Writes',
	         style: { fontSize: '12px' },
	      },
	      xAxis: {
	         categories: ['1', '2', '3', '4', '5']
	      },
	      yAxis: {
	    	  title: {
	            text: 'KB'
	         }
	      },
	      tooltip: {
	         formatter: function() {
	            return ''+
	                this.series.name +': '+ this.y +'';
	         }
	      },
	      legend: {
		    	 enabled:false,
		    },
		  credits:{ enabled:false },
		  plotOptions:{series:{marker: {enabled: false}} },
	      credits: {
	         enabled: false
	      },
	      series: [{
	         name: 'Read',
	         data: [200, 175, 170, 150, 180, 178 , 178]
	      }, {
	         name: 'Write',
	         data: [-150, -125, -125, -120, -135, -128, -140]
	      }]
	   });
        /*var count = 0;
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
                obj_db_Line_MemoryUsage_Data.yAxis.title.text = 'KB';
                obj_db_Line_MemoryUsage_Data.title.text = "Memory Usage";
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_db_Line_MemoryUsage_Data);
        		}
        		chart = new Highcharts.Chart(obj_db_Line_MemoryUsage_Data);
        });*/
}

/*****************************************************************************/
//Function for disk read - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Line_DiskRead_Data = function(isZoom)
 {
	 chart = new Highcharts.Chart({
	      chart: {
	         renderTo: 'avgReadDiv',
	         defaultSeriesType: 'area',
	         marginLeft: '50',
	     	 width: '250',
	         height: '200',
	     	 style:{ width:'100%',  height:'210', position: 'inherit' },
	         marginRight: 0,
	         marginBottom: 35,
	         zoomType: 'xy'
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
	         text: 'IOPS',
	         style: { fontSize: '12px' },
	      },
	      xAxis: {
	         categories: ['1', '2', '3', '4', '5', '6', '7'],
	         tickmarkPlacement: 'on',
	         title: {
	            enabled: false
	         }
	      },
	      yAxis: {
	         title: {
	            text: 'IOPs'
	         },
	         /*labels: {
	            formatter: function() {
	               return this.value / 1000;
	            }
	         }*/
	      },
	      tooltip: {
	         formatter: function() {
	            return ''+
	                this.x +': '+ Highcharts.numberFormat(this.y, 0, ',') +' ';
	         }
	      },
	      legend:{enabled:false},
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
	         name: 'Read',
	         data: [90, 100, 120, 110, 65, 70, 70]
	      }, {
	         name: 'Write',
	         data: [65, 70, 80, 68, 67, 65, 65]
	      }, {
		     name: 'Stat',
		     data: [50, 52, 55, 55, 52, 52, 48]
		  }, {
		      name: 'Close',
		      data: [40, 42, 45, 44, 43, 42, 41]
		  }, {
			 name: 'Open',
			 data: [20, 25, 30, 22, 24, 25, 26]
		  }]
	 });
       /* var count = 0;
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
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_db_Line_DiskRead_Data);
        		}
                chart = new Highcharts.Chart(obj_db_Line_DiskRead_Data);
        });*/
}

/*****************************************************************************/
//Function for disk write - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/

 db_Line_DiskWrite_Data = function(isZoom)
 {
        /*var count = 0;
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
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_db_Line_DiskWrite_Data);
        		}
                chart = new Highcharts.Chart(obj_db_Line_DiskWrite_Data);
        });*/
}   

/*****************************************************************************/
//Function for cpu usage for MDS/MGS - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Mgs_Line_CpuUsage_Data = function(isZoom)
 {
	 var chart = new Highcharts.Chart({
		    chart: {
		        renderTo: 'mgsavgCPUDiv',
		    	marginLeft: '50',
  		width: '250',
  	    height: '200',
  		style:{ width:'100%',  height:'210', position: 'inherit' },
  	    marginBottom: 35,
  	    zoomType: 'xy'
			},
			
		    title: {
		         text: 'Server CPU and Memory',
		         style: { fontSize: '12px' },
		    },
		    xAxis: {
		        categories: ['01:35:00', '01:35:10', '01:35:20', '01:35:30', '01:35:40', '01:35:50', '01:35:60', '01:35:70', '01:35:80', '01:35:90'],
		        labels: {rotation: 310,step: 2,style:{fontSize:'8px', fontWeight:'bold'}}
		    },
		    yAxis: [{
		        title: {
		            text: 'KB'
		        },
		        opposite: true,
		    },{
		        title: {
		            text: 'Percentage'
		        },
		        
		        max:100, min:0, startOnTick:false,  tickInterval: 20
		    }],
		    legend: {
		    	 enabled:false,
		    },
		    credits:{ enabled:false },
		    plotOptions:{series:{marker: {enabled: true}} },
		    series: [{
		        type: 'column',
		        data: [20, 40, 35, 52, 70, 60, 42, 50, 50, 45],
		        name: 'KB',
		        yAxis: 1
		    },{
		        type: 'line',
		        data: [35, 35, 32, 35, 33, 33, 33, 35, 35, 35],
		        name: 'Percentage',
		    }]
		});
        /*var count = 0;
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
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_db_Mgs_Line_CpuUsage_Data);
        		}
                chart = new Highcharts.Chart(obj_db_Mgs_Line_CpuUsage_Data);
        });*/
    }

/*****************************************************************************/
//Function for memory usage for MDS/MGS - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Mgs_Line_MemoryUsage_Data = function(isZoom)
 {
	 chart = new Highcharts.Chart({
	      chart: {
	         renderTo: 'mgsavgMemoryDiv',
	         defaultSeriesType: 'area',
	         marginLeft: '50',
	     	 width: '250',
	         height: '200',
	     	 style:{ width:'100%',  height:'210', position: 'inherit' },
	         marginRight: 0,
	         marginBottom: 35,
	         zoomType: 'xy'
	      },
	      colors: [
			     	'#628EC5', 
			     	'#AE91D0', 
			     	'#A6C56D', 
			     	'#C76560', 
			     	'#3D96AE', 
			     	'#DB843D', 
			     	'#92A8CD', 
			     	'#A47D7C', 
			     	'#B5CA92'
			     ],
	      title: {
	         text: 'Read Vs Writes',
	         style: { fontSize: '12px' },
	      },
	      xAxis: {
	         categories: ['1', '2', '3', '4', '5']
	      },
	      yAxis: {
	    	  title: {
	            text: 'KB'
	         }
	      },
	      tooltip: {
	         formatter: function() {
	            return ''+
	                this.series.name +': '+ this.y +'';
	         }
	      },
	      legend: {
		    	 enabled:false,
		    },
		  credits:{ enabled:false },
		  plotOptions:{series:{marker: {enabled: false}} },
	      credits: {
	         enabled: false
	      },
	      series: [{
	         name: 'Read',
	         data: [20, 30, 30, 50, 50, 60 , 70]
	      }, {
	         name: 'Write',
	         data: [-50, -45, -65, -70, -75, -78, -50]
	      }],
	      exporting:{
	    	  enabled: true
	      }
	   });
       /* var count = 0;
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
                obj_db_Mgs_Line_MemoryUsage_Data.yAxis.title.text = 'KB';
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_db_Mgs_Line_MemoryUsage_Data);
        		}
                chart = new Highcharts.Chart(obj_db_Mgs_Line_MemoryUsage_Data);
        });*/
}

/*****************************************************************************/
//Function for disk read for MDS/MGS - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/
 db_Mgs_Line_DiskRead_Data = function(isZoom)
 {
	 chart = new Highcharts.Chart({
	      chart: {
	         renderTo: 'heatMapDiv', 
	         defaultSeriesType: 'scatter',
	         marginLeft: '50',
	     	 width: '500',
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
	         }
	      },
	      tooltip: {
	         formatter: function() {
	                   return ''+
	               this.x +' , '+ this.y +' ';
	         }
	      },
	      legend: {
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
	      series: [{
	         name: 'Usage',
	         color: 'rgb(212, 139, 135)',
	         data: [[161.2, 51.6], [167.5, 59.0], [159.5, 49.2], [157.0, 63.0], [155.8, 53.6], 
	            [170.0, 59.0], [159.1, 47.6], [166.0, 69.8], [176.2, 66.8], [160.2, 75.2], 
	            [172.5, 55.2], [170.9, 54.2], [172.9, 62.5], [153.4, 42.0], [160.0, 50.0], 
	            [147.2, 49.8], [168.2, 49.2], [175.0, 73.2], [157.0, 47.8], [167.6, 68.8], 
	            [159.5, 50.6], [175.0, 82.5], [166.8, 57.2], [176.5, 87.8], [170.2, 72.8], 
	            [174.0, 54.5], [173.0, 59.8], [179.9, 67.3], [170.5, 67.8], [160.0, 47.0], 
	            [154.4, 46.2], [162.0, 55.0], [176.5, 83.0], [160.0, 54.4], [152.0, 45.8], 
	            [162.1, 53.6], [170.0, 73.2], [160.2, 52.1], [161.3, 67.9], [166.4, 56.6], 
	            [168.9, 62.3], [163.8, 58.5], [167.6, 54.5], [160.0, 50.2], [161.3, 60.3], 
	            [167.6, 58.3], [165.1, 56.2], [160.0, 50.2], [170.0, 72.9], [157.5, 59.8], 
	            [167.6, 61.0], [160.7, 69.1], [163.2, 55.9], [152.4, 46.5], [157.5, 54.3], 
	            [168.3, 54.8], [180.3, 60.7], [165.5, 60.0], [165.0, 62.0], [164.5, 60.3], 
	            [156.0, 52.7], [160.0, 74.3], [163.0, 62.0], [165.7, 73.1], [161.0, 80.0], 
	            [162.0, 54.7], [166.0, 53.2], [174.0, 75.7], [172.7, 61.1], [167.6, 55.7], 
	            [151.1, 48.7], [164.5, 52.3], [163.5, 50.0], [152.0, 59.3], [169.0, 62.5], 
	            [164.0, 55.7], [161.2, 54.8], [155.0, 45.9], [170.0, 70.6], [176.2, 67.2], 
	            [170.0, 69.4], [162.5, 58.2], [170.3, 64.8], [164.1, 71.6], [169.5, 52.8], 
	            [163.2, 59.8], [154.5, 49.0], [159.8, 50.0], [173.2, 69.2], [170.0, 55.9], 
	            [161.4, 63.4], [169.0, 58.2], [166.2, 58.6], [159.4, 45.7], [162.5, 52.2], 
	            [159.0, 48.6], [162.8, 57.8], [159.0, 55.6], [179.8, 66.8], [162.9, 59.4], 
	            [161.0, 53.6], [151.1, 73.2], [168.2, 53.4], [168.9, 69.0], [173.2, 58.4], 
	            [171.8, 56.2], [178.0, 70.6], [164.3, 59.8], [163.0, 72.0], [168.5, 65.2], 
	            [166.8, 56.6], [172.7, 105.2], [163.5, 51.8], [169.4, 63.4], [167.8, 59.0], 
	            [159.5, 47.6], [167.6, 63.0], [161.2, 55.2], [160.0, 45.0], [163.2, 54.0], 
	            [162.2, 50.2], [161.3, 60.2], [149.5, 44.8], [157.5, 58.8], [163.2, 56.4], 
	            [172.7, 62.0], [155.0, 49.2], [156.5, 67.2], [164.0, 53.8], [160.9, 54.4], 
	            [162.8, 58.0], [167.0, 59.8], [160.0, 54.8], [160.0, 43.2], [168.9, 60.5], 
	            [158.2, 46.4], [156.0, 64.4], [160.0, 48.8], [167.1, 62.2], [158.0, 55.5], 
	            [167.6, 57.8], [156.0, 54.6], [162.1, 59.2], [173.4, 52.7], [159.8, 53.2], 
	            [170.5, 64.5], [159.2, 51.8], [157.5, 56.0], [161.3, 63.6], [162.6, 63.2], 
	            [160.0, 59.5], [168.9, 56.8], [165.1, 64.1], [162.6, 50.0], [165.1, 72.3], 
	            [166.4, 55.0], [160.0, 55.9], [152.4, 60.4], [170.2, 69.1], [162.6, 84.5], 
	            [170.2, 55.9], [158.8, 55.5], [172.7, 69.5], [167.6, 76.4], [162.6, 61.4], 
	            [167.6, 65.9], [156.2, 58.6], [175.2, 66.8], [172.1, 56.6], [162.6, 58.6], 
	            [160.0, 55.9], [165.1, 59.1], [182.9, 81.8], [166.4, 70.7], [165.1, 56.8], 
	            [177.8, 60.0], [165.1, 58.2], [175.3, 72.7], [154.9, 54.1], [158.8, 49.1], 
	            [172.7, 75.9], [168.9, 55.0], [161.3, 57.3], [167.6, 55.0], [165.1, 65.5], 
	            [175.3, 65.5], [157.5, 48.6], [163.8, 58.6], [167.6, 63.6], [165.1, 55.2], 
	            [165.1, 62.7], [168.9, 56.6], [162.6, 53.9], [164.5, 63.2], [176.5, 73.6], 
	            [168.9, 62.0], [175.3, 63.6], [159.4, 53.2], [160.0, 53.4], [170.2, 55.0], 
	            [162.6, 70.5], [167.6, 54.5], [162.6, 54.5], [160.7, 55.9], [160.0, 59.0], 
	            [157.5, 63.6], [162.6, 54.5], [152.4, 47.3], [170.2, 67.7], [165.1, 80.9], 
	            [172.7, 70.5], [165.1, 60.9], [170.2, 63.6], [170.2, 54.5], [170.2, 59.1], 
	            [161.3, 70.5], [167.6, 52.7], [167.6, 62.7], [165.1, 86.3], [162.6, 66.4], 
	            [152.4, 67.3], [168.9, 63.0], [170.2, 73.6], [175.2, 62.3], [175.2, 57.7], 
	            [160.0, 55.4], [165.1, 104.1], [174.0, 55.5], [170.2, 77.3], [160.0, 80.5], 
	            [167.6, 64.5], [167.6, 72.3], [167.6, 61.4], [154.9, 58.2], [162.6, 81.8], 
	            [175.3, 63.6], [171.4, 53.4], [157.5, 54.5], [165.1, 53.6], [160.0, 60.0], 
	            [174.0, 73.6], [162.6, 61.4], [174.0, 55.5], [162.6, 63.6], [161.3, 60.9], 
	            [156.2, 60.0], [149.9, 46.8], [169.5, 57.3], [160.0, 64.1], [175.3, 63.6], 
	            [169.5, 67.3], [160.0, 75.5], [172.7, 68.2], [162.6, 61.4], [157.5, 76.8], 
	            [176.5, 71.8], [164.4, 55.5], [160.7, 48.6], [174.0, 66.4], [163.8, 67.3]]
	   
	      }]
	   });
        /*var count = 0;
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
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_db_Mgs_Line_DiskRead_Data);
        		}
                chart = new Highcharts.Chart(obj_db_Mgs_Line_DiskRead_Data);
        });*/
}

 /*****************************************************************************/
//Function for disk write for MDS/MGS - Line Chart
//Param - File System name, start date, end date, datafunction (average/min/max)
//Return - Returns the graph plotted in container
/*****************************************************************************/

 db_Mgs_Line_DiskWrite_Data = function(isZoom)
 {
        /*var count = 0;
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
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_db_Mgs_Line_DiskWrite_Data);
        		}
                chart = new Highcharts.Chart(obj_db_Mgs_Line_DiskWrite_Data);
        });*/
        
        renderZoomDialog = function(object)
        {
        	object.xAxis.labels.style = 'fontSize:12px';
        	object.yAxis.labels={style:{fontSize:'12px', fontWeight:'bold'}};
        	object.chart.width = "780";
        	object.chart.height = "360";
        	object.chart.style.height = "360";
        	object.chart.style.width = "100%";
        	object.chart.renderTo = "zoomDialog";
        }
        
        setZoomDialogTitle = function(titleName)
    	{
        	$('#zoomDialog').dialog('option', 'title', titleName);
    		$('#zoomDialog').dialog('open');
    	}
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
