/*******************************************************************************/
// File name: custom_dashboard.js
// Description:
//
/*******************************************************************************/
var barGraphOptions = 
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
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
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
var pieDataOptions = 
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
var lineDataOptions_CPUUsage = 
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '250',
	style:{ width:'100%',  height:'200px', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', x: -20, style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{ layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 10,borderWidth: 0},
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
var lineDataOptions_MemoryUsage =
{
    chart:{
    renderTo: '',
    marginLeft: '50',
    width: '250',
    style:{ width:'100%',  height:'200px', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', x: -20, style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{ layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 10,borderWidth: 0},
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
var lineDataOptions_DiskRead =
{
    chart:{
    renderTo: '',
    marginLeft: '50',
    width: '250',
    style:{ width:'100%',  height:'200px', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', x: -20, style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{ layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 10,borderWidth: 0},
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
var lineDataOptions_DiskWrite =
{
    chart:{
    renderTo: '',
    marginLeft: '50',
    width: '250',
    style:{ width:'100%',  height:'200px', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', x: -20, style: { fontSize: '12px' }, },
    zoomType: 'xy', 
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{ layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 10,borderWidth: 0},
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
var lineDataOptions_Mgs_CPUUsage =
{
    chart:{
    renderTo: '',
    marginLeft: '50',
    width: '250',
    style:{ width:'100%',  height:'200px', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', x: -20, style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{ layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 10,borderWidth: 0},
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
var lineDataOptions_Mgs_MemoryUsage =
{
    chart:{
    renderTo: '',
    marginLeft: '50',
    width: '250',
    style:{ width:'100%',  height:'200px', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', x: -20, style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{ layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 10,borderWidth: 0},
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
var lineDataOptions_Mgs_DiskRead =
{
    chart:{
    renderTo: '',
    marginLeft: '50',
    width: '250',
    style:{ width:'100%',  height:'200px', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', x: -20, style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{ layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 10,borderWidth: 0},
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
var lineDataOptions_Mgs_DiskWrite =
{
    chart:{
    renderTo: '',
    marginLeft: '50',
    width: '250',
    style:{ width:'100%',  height:'200px', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 25,
    zoomType: 'xy'
    },
    title:{ text: '', x: -20, style: { fontSize: '12px' }, },
    zoomType: 'xy',
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    legend:{ layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 10,borderWidth: 0},
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
// Space Usage - Bar chart
/*****************************************************************************/
load_landingPageBar_disk = function(isZoom)
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
			    var fName = '';
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
			obj_db_landingPageBar = barGraphOptions;
			if(isZoom == 'true')
			{
				obj_db_landingPageBar.chart.width = "780";
				obj_db_landingPageBar.chart.height = "360";
				obj_db_landingPageBar.chart.style.height = "360";
				obj_db_landingPageBar.chart.style.width = "100%";
				obj_db_landingPageBar.chart.renderTo = "dialog_container";
			}
			else
			{
				obj_db_landingPageBar.chart.renderTo = "container";
			}
            obj_db_landingPageBar.xAxis.categories = categories;
            obj_db_landingPageBar.title.text="All File System Space Usage";
            obj_db_landingPageBar.yAxis.title.text = '%';
            obj_db_landingPageBar.xAxis.labels = {
                    rotation: 310,
            }
            obj_db_landingPageBar.series = [
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
            chart = new Highcharts.Chart(obj_db_landingPageBar);
        });
    }
/*****************************************************************************/
//  Space Usage - Pie chart
/*****************************************************************************/
    load_landingPagePie_disk = function()
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
            obj_db_landingPagePie = pieDataOptions;
            obj_db_landingPagePie.title.text="All File System Space Usage";
            obj_db_landingPagePie.chart.renderTo = "container2";
            obj_db_landingPagePie.series = [{
                type: 'pie',
                name: 'Browser share',
                data: [
                    ['Free',    free],
                    ['Used',    used]
                    ]
                }];
            chart = new Highcharts.Chart(obj_db_landingPagePie);
        });
    }
/*****************************************************************************/
// Files Vs Free Nodes - Bar chart
/*****************************************************************************/
load_landingPageBar_inodes = function()
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
            load_landingPageBar_inodes = barGraphOptions;
            load_landingPageBar_inodes.xAxis.categories = categories;
            load_landingPageBar_inodes.title.text="Files Vs Free Nodes";
            load_landingPageBar_inodes.yAxis.title.text = '%';
            load_landingPageBar_inodes.chart.renderTo = "container1";
            load_landingPageBar_inodes.xAxis.labels = {
                    rotation: 310,
            }
            load_landingPageBar_inodes.series = [
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
            chart = new Highcharts.Chart(load_landingPageBar_inodes);
        });
    }
/*****************************************************************************/
//	Files Vs Free Nodes - Pie chart
/*****************************************************************************/
    load_landingPagePie_indoes = function()
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
           load_landingPagePie_indoes = pieDataOptions;
           load_landingPagePie_indoes.title.text="Files Vs Free Nodes";
           load_landingPagePie_indoes.chart.renderTo = "container3";       
           load_landingPagePie_indoes.series = [{
               type: 'pie',
               name: 'Browser share',
               data: [
                  ['Free',    free],
                  ['Used',    used]
               ]
            }];
            chart = new Highcharts.Chart(load_landingPagePie_indoes);
        });
     }

/*****************************************************************************/
// All File System CPU Usage - Line Chart
/*****************************************************************************/
load_LineChart_CpuUsage = function(isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
		obj_gn_line_CPUUsage = lineDataOptions_CPUUsage;
		if(isZoom == 'true')
		{
			obj_gn_line_CPUUsage.chart.width = "780";
			obj_gn_line_CPUUsage.chart.height = "360";
			obj_gn_line_CPUUsage.chart.style.height = "360";
			obj_gn_line_CPUUsage.chart.style.width = "100%";
			obj_gn_line_CPUUsage.chart.renderTo = "dialog_avgCPUDiv";
		}
		else
		{
			obj_gn_line_CPUUsage.chart.renderTo = "avgCPUDiv";
		}
		
        obj_gn_line_CPUUsage.title.text="CPU Usage";
        $.post("/api/getservercpuusage/",{datafunction: "average", hostname: "", endtime: "29-20-2011", starttime: "29-20-2011"})
         .success(function(data, textStatus, jqXHR) 
          {
            var ostName='';
            var avgCPUApiResponse = data;
            if(avgCPUApiResponse.success)
            {
                 var response = avgCPUApiResponse.response;
                 $.each(response, function(resKey, resValue) 
                {
		          if (ostName != resValue.hostname && ostName !='')
		          {
		          obj_gn_line_CPUUsage.series[count] = {
		                name: ostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          ostName = resValue.hostname;
		          optionData.push(resValue.cpu);
		          categories.push(resValue.timestamp);
			       }
			       else
			       {
			        ostName = resValue.hostname;
			        optionData.push(resValue.cpu);
			        categories.push(resValue.timestamp);
			       }
			     });
                 obj_gn_line_CPUUsage.series[count] = { name: ostName, data: optionData };
            }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_gn_line_CPUUsage.xAxis.categories = categories;
                obj_gn_line_CPUUsage.yAxis.title.text = '%';
                obj_gn_line_CPUUsage.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_gn_line_CPUUsage);
        });
    }

/*****************************************************************************/
// All File System Memory Usage - Line Chart
/*****************************************************************************/
load_LineChart_MemoryUsage = function()
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_gn_line_MemoryUsage = lineDataOptions_MemoryUsage;
        obj_gn_line_MemoryUsage.title.text = "Memory Usage";
        obj_gn_line_MemoryUsage.chart.renderTo = "avgMemoryDiv";
        $.post("/api/getservermemoryusage/",{datafunction: "average", hostname: "", endtime: "29-20-2011", starttime: "29-20-2011"})
         .success(function(data, textStatus, jqXHR) {
            var ostName='';
            var avgMemoryApiResponse = data;
            if(avgMemoryApiResponse.success)
             {
                 var response = avgMemoryApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (ostName != resValue.hostname && ostName !='')
		          {
		          obj_gn_line_MemoryUsage.series[count] = {
		                name: ostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          ostName = resValue.hostname;
		          optionData.push(resValue.memory);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            ostName = resValue.hostname;
		            optionData.push(resValue.memory);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_gn_line_MemoryUsage.series[count] = { name: ostName, data: optionData };
		      }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_gn_line_MemoryUsage.xAxis.categories = categories;
                obj_gn_line_MemoryUsage.yAxis.title.text = 'GB';
                obj_gn_line_MemoryUsage.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_gn_line_MemoryUsage);
        });
}

/*****************************************************************************/
// All File System Disk Read - Line Chart
/*****************************************************************************/
load_LineChart_DiskRead = function()
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_gn_line_DiskRead = lineDataOptions_DiskRead;
        obj_gn_line_DiskRead.title.text = "Disk Read";
        obj_gn_line_DiskRead.chart.renderTo = "avgReadDiv";
        $.post("/api/gettargetreads/",{datafunction: "average", endtime: "29-20-2011", targetname: "", hostname: "", starttime: "29-20-2011"})
         .success(function(data, textStatus, jqXHR) {
            var ostName='';
            var avgDiskReadApiResponse = data;
            if(avgDiskReadApiResponse.success)
             {
                 var response = avgDiskReadApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (ostName != resValue.targetname && ostName !='')
		          {
		          obj_gn_line_DiskRead.series[count] = {
		                name: ostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          ostName = resValue.targetname;
		          optionData.push(resValue.reads);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            ostName = resValue.targetname;
		            optionData.push(resValue.reads);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_gn_line_DiskRead.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_gn_line_DiskRead.xAxis.categories = categories;
                obj_gn_line_DiskRead.yAxis.title.text = 'KB';
                obj_gn_line_DiskRead.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_gn_line_DiskRead);
        });
}

/*****************************************************************************/
// All File System Disk Write - Line Chart
/*****************************************************************************/

load_LineChart_DiskWrite = function()
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_gn_line_DiskWrite = lineDataOptions_DiskWrite;
        obj_gn_line_DiskWrite.title.text = "Disk Write";
        obj_gn_line_DiskWrite.chart.renderTo = "avgWriteDiv";
        $.post("/api/gettargetwrites/",{datafunction: "average", endtime: "29-20-2011", targetname: "", hostname: "", starttime: "29-20-2011"})
         .success(function(data, textStatus, jqXHR) {
            var ostName='';
            var avgDiskWriteApiResponse = data;
            if(avgDiskWriteApiResponse.success)
             {
                 var response = avgDiskWriteApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (ostName != resValue.targetname && ostName !='')
		          {
		          obj_gn_line_DiskWrite.series[count] = {
		                name: ostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          ostName = resValue.targetname;
		          optionData.push(resValue.writes);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            ostName = resValue.targetname;
		            optionData.push(resValue.writes);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_gn_line_DiskWrite.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_gn_line_DiskWrite.xAxis.categories = categories;
                obj_gn_line_DiskWrite.yAxis.title.text = 'KB';
                obj_gn_line_DiskWrite.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_gn_line_DiskWrite);
        });
}   

/*****************************************************************************/
// All MGS/MGT CPU Usage - Line Chart
/*****************************************************************************/
load_LineChart_Mgs_CpuUsage = function()
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_gn_line_Mgs_CPUUsage = lineDataOptions_Mgs_CPUUsage;
        obj_gn_line_Mgs_CPUUsage.title.text="CPU Usage";
        obj_gn_line_Mgs_CPUUsage.chart.renderTo = "mgsavgCPUDiv";
        $.post("/api/getservercpuusage/",{datafunction: "average", hostname: "", endtime: "29-20-2011", starttime: "29-20-2011"})
         .success(function(data, textStatus, jqXHR) {
            var ostName='';
            var avgCPUApiResponse = data;
            if(avgCPUApiResponse.success)
             {
                 var response = avgCPUApiResponse.response;
                 $.each(response, function(resKey, resValue) 
                {
		          if (ostName != resValue.hostname && ostName !='')
		          {
		          obj_gn_line_Mgs_CPUUsage.series[count] = {
		                name: ostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          ostName = resValue.hostname;
		          optionData.push(resValue.cpu);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            ostName = resValue.hostname;
		            optionData.push(resValue.cpu);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_gn_line_Mgs_CPUUsage.series[count] = { name: ostName, data: optionData };
             }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_gn_line_Mgs_CPUUsage.xAxis.categories = categories;
                obj_gn_line_Mgs_CPUUsage.yAxis.title.text = '%';
                obj_gn_line_Mgs_CPUUsage.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_gn_line_Mgs_CPUUsage);
        });
    }

/*****************************************************************************/
// All MGS/MGT Memory Usage - Line Chart
/*****************************************************************************/
load_LineChart_Mgs_MemoryUsage = function()
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_gn_line_Mgs_MemoryUsage = lineDataOptions_Mgs_MemoryUsage;
        obj_gn_line_Mgs_MemoryUsage.title.text = "Memory Usage";
        obj_gn_line_Mgs_MemoryUsage.chart.renderTo = "mgsavgMemoryDiv";
        $.post("/api/getservermemoryusage/",{datafunction: "average", hostname: "", endtime: "29-20-2011", starttime: "29-20-2011"})
         .success(function(data, textStatus, jqXHR) {
            var ostName='';
            var avgMemoryApiResponse = data;
            if(avgMemoryApiResponse.success)
             {
                 var response = avgMemoryApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (ostName != resValue.hostname && ostName !='')
		          {
		          obj_gn_line_Mgs_MemoryUsage.series[count] = {
		                name: ostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          ostName = resValue.hostname;
		          optionData.push(resValue.memory);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            ostName = resValue.hostname;
		            optionData.push(resValue.memory);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_gn_line_Mgs_MemoryUsage.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_gn_line_Mgs_MemoryUsage.xAxis.categories = categories;
                obj_gn_line_Mgs_MemoryUsage.yAxis.title.text = 'GB';
                obj_gn_line_Mgs_MemoryUsage.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_gn_line_Mgs_MemoryUsage);
        });
}

/*****************************************************************************/
// All MGS/MGT Disk Read - Line Chart
/*****************************************************************************/
load_LineChart_Mgs_DiskRead = function()
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_gn_line_Mgs_DiskRead = lineDataOptions_Mgs_DiskRead;
        obj_gn_line_Mgs_DiskRead.title.text = "Disk Read";
        obj_gn_line_Mgs_DiskRead.chart.renderTo = "mgsavgReadDiv";
        $.post("/api/gettargetreads/",{datafunction: "average", endtime: "29-20-2011", targetname: "", hostname: "", starttime: "29-20-2011"})
         .success(function(data, textStatus, jqXHR) {
            var ostName='';
            var avgDiskReadApiResponse = data;
            if(avgDiskReadApiResponse.success)
             {
                 var response = avgDiskReadApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (ostName != resValue.targetname && ostName !='')
		          {
		          obj_gn_line_Mgs_DiskRead.series[count] = {
		                name: ostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          ostName = resValue.targetname;
		          optionData.push(resValue.reads);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            ostName = resValue.targetname;
		            optionData.push(resValue.reads);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_gn_line_Mgs_DiskRead.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_gn_line_Mgs_DiskRead.xAxis.categories = categories;
                obj_gn_line_Mgs_DiskRead.yAxis.title.text = 'KB';
                obj_gn_line_Mgs_DiskRead.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_gn_line_Mgs_DiskRead);
        });
}

/*****************************************************************************/
// All MGS/MGT Disk Write - Line Chart
/*****************************************************************************/

load_LineChart_Mgs_DiskWrite = function()
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_gn_line_Mgs_DiskWrite = lineDataOptions_Mgs_DiskWrite;
        obj_gn_line_Mgs_DiskWrite.title.text = "Disk Write";
        obj_gn_line_Mgs_DiskWrite.chart.renderTo = "mgsavgWriteDiv";
        $.post("/api/gettargetwrites/",{datafunction: "average", endtime: "29-20-2011", targetname: "", hostname: "", starttime: "29-20-2011"})
         .success(function(data, textStatus, jqXHR) {
            var ostName='';
            var avgDiskWriteApiResponse = data;
            if(avgDiskWriteApiResponse.success)
             {
                 var response = avgDiskWriteApiResponse.response;
                 $.each(response, function(resKey, resValue)
                {
		          if (ostName != resValue.targetname && ostName !='')
		          {
		          obj_gn_line_Mgs_DiskWrite.series[count] = {
		                name: ostName,
		                data: optionData
		                   };
		          optionData = [];
		          categories = [];
		          count++;
		          ostName = resValue.targetname;
		          optionData.push(resValue.writes);
		          categories.push(resValue.timestamp);
		          }
		           else
		           {
		            ostName = resValue.targetname;
		            optionData.push(resValue.writes);
		            categories.push(resValue.timestamp);
		           }
		          });
                 obj_gn_line_Mgs_DiskWrite.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_gn_line_Mgs_DiskWrite.xAxis.categories = categories;
                obj_gn_line_Mgs_DiskWrite.yAxis.title.text = 'KB';
                obj_gn_line_Mgs_DiskWrite.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_gn_line_Mgs_DiskWrite);
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
