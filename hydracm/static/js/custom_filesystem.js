/*******************************************************************************/
// File name: custom_filesystem.js
// Description: Plots all the graphs for the file system dashboard
//
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
var fs_lineOptions_CPUUsage = 
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
var fs_lineOptions_MemoryUsage =
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
var fs_lineOptions_DiskRead =
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
var fs_lineOptions_DiskWrite =
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
var fs_lineOptions_Mgs_CPUUsage =
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
var fs_lineOptions_Mgs_MemoryUsage =
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
var fs_lineOptions_Mgs_DiskRead =
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
var fs_lineOptions_Mgs_DiskWrite =
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
//  Space Usage - Pie chart
/*****************************************************************************/
    load_fsPagePie_disk = function(fsName, sDate, eDate, dataFunction)
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
            obj_db_landingPagePie = pieDataOptions;
            obj_db_landingPagePie.title.text="All File System Space Usage";
            obj_db_landingPagePie.chart.renderTo = "fs_container2";
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
//	Files Vs Free Nodes - Pie chart
/*****************************************************************************/
    load_fsPagePie_indoes = function(fsName, sDate, eDate, dataFunction)
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
           load_landingPagePie_indoes = pieDataOptions;
           load_landingPagePie_indoes.title.text="Files Vs Free Nodes";
           load_landingPagePie_indoes.chart.renderTo = "fs_container3";       
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
load_fsPageLine_CpuUsage = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_line_CPUUsage = fs_lineOptions_CPUUsage;
        obj_fs_line_CPUUsage.title.text="CPU Usage";
        obj_fs_line_CPUUsage.chart.renderTo = "fs_avgCPUDiv";
        $.post("/api/getservercpuusage/",{datafunction: dataFunction, hostname: "", endtime: eDate, starttime: sDate})
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
		          obj_fs_line_CPUUsage.series[count] = {
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
                 obj_fs_line_CPUUsage.series[count] = { name: ostName, data: optionData };
            }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_line_CPUUsage.xAxis.categories = categories;
                obj_fs_line_CPUUsage.yAxis.title.text = '%';
                obj_fs_line_CPUUsage.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_fs_line_CPUUsage);
        });
    }

/*****************************************************************************/
// All File System Memory Usage - Line Chart
/*****************************************************************************/
load_fsPageLine_MemoryUsage = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_fs_line_MemoryUsage = fs_lineOptions_MemoryUsage;
        obj_fs_line_MemoryUsage.title.text = "Memory Usage";
        obj_fs_line_MemoryUsage.chart.renderTo = "fs_avgMemoryDiv";
        $.post("/api/getservermemoryusage/",{datafunction: dataFunction, hostname: "", endtime: eDate, starttime: sDate})
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
		          obj_fs_line_MemoryUsage.series[count] = {
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
                 obj_fs_line_MemoryUsage.series[count] = { name: ostName, data: optionData };
		      }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_line_MemoryUsage.xAxis.categories = categories;
                obj_fs_line_MemoryUsage.yAxis.title.text = 'GB';
                obj_fs_line_MemoryUsage.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_fs_line_MemoryUsage);
        });
}

/*****************************************************************************/
// All File System Disk Read - Line Chart
/*****************************************************************************/
load_fsPageLine_DiskRead = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_line_DiskRead = fs_lineOptions_DiskRead;
        obj_fs_line_DiskRead.title.text = "Disk Read";
        obj_fs_line_DiskRead.chart.renderTo = "fs_avgReadDiv";
        $.post("/api/gettargetreads/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
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
		          obj_fs_line_DiskRead.series[count] = {
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
                 obj_fs_line_DiskRead.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_line_DiskRead.xAxis.categories = categories;
                obj_fs_line_DiskRead.yAxis.title.text = 'KB';
                obj_fs_line_DiskRead.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_fs_line_DiskRead);
        });
}

/*****************************************************************************/
// All File System Disk Write - Line Chart
/*****************************************************************************/

load_fsPageLine_DiskWrite = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_line_DiskWrite = fs_lineOptions_DiskWrite;
        obj_fs_line_DiskWrite.title.text = "Disk Write";
        obj_fs_line_DiskWrite.chart.renderTo = "fs_avgWriteDiv";
        $.post("/api/gettargetwrites/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
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
		          obj_fs_line_DiskWrite.series[count] = {
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
                 obj_fs_line_DiskWrite.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_line_DiskWrite.xAxis.categories = categories;
                obj_fs_line_DiskWrite.yAxis.title.text = 'KB';
                obj_fs_line_DiskWrite.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_fs_line_DiskWrite);
        });
}   

/*****************************************************************************/
// All MDS/MGS CPU Usage - Line Chart
/*****************************************************************************/
load_fsPageLine_Mgs_CpuUsage = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_fs_line_Mgs_CPUUsage = fs_lineOptions_Mgs_CPUUsage;
        obj_fs_line_Mgs_CPUUsage.title.text="CPU Usage";
        obj_fs_line_Mgs_CPUUsage.chart.renderTo = "fs_mgsavgCPUDiv";
        $.post("/api/getservercpuusage/",{datafunction: dataFunction, hostname: "", endtime: eDate, starttime: sDate})
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
		          obj_fs_line_Mgs_CPUUsage.series[count] = {
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
                 obj_fs_line_Mgs_CPUUsage.series[count] = { name: ostName, data: optionData };
             }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_line_Mgs_CPUUsage.xAxis.categories = categories;
                obj_fs_line_Mgs_CPUUsage.yAxis.title.text = '%';
                obj_fs_line_Mgs_CPUUsage.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_fs_line_Mgs_CPUUsage);
        });
    }

/*****************************************************************************/
// All MDS/MGS Memory Usage - Line Chart
/*****************************************************************************/
load_fsPageLine_Mgs_MemoryUsage = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
         var optionData = [],categories = [];
        obj_fs_line_Mgs_MemoryUsage = fs_lineOptions_Mgs_MemoryUsage;
        obj_fs_line_Mgs_MemoryUsage.title.text = "Memory Usage";
        obj_fs_line_Mgs_MemoryUsage.chart.renderTo = "fs_mgsavgMemoryDiv";
        $.post("/api/getservermemoryusage/",{datafunction: dataFunction, hostname: "", endtime: eDate, starttime: sDate})
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
		          obj_fs_line_Mgs_MemoryUsage.series[count] = {
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
                 obj_fs_line_Mgs_MemoryUsage.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_line_Mgs_MemoryUsage.xAxis.categories = categories;
                obj_fs_line_Mgs_MemoryUsage.yAxis.title.text = 'GB';
                obj_fs_line_Mgs_MemoryUsage.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_fs_line_Mgs_MemoryUsage);
        });
}

/*****************************************************************************/
// All MDS/MGS Disk Read - Line Chart
/*****************************************************************************/
load_fsPageLine_Mgs_DiskRead = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_line_Mgs_DiskRead = fs_lineOptions_Mgs_DiskRead;
        obj_fs_line_Mgs_DiskRead.title.text = "Disk Read";
        obj_fs_line_Mgs_DiskRead.chart.renderTo = "fs_mgsavgReadDiv";
        $.post("/api/gettargetreads/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
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
		          obj_fs_line_Mgs_DiskRead.series[count] = {
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
                 obj_fs_line_Mgs_DiskRead.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_line_Mgs_DiskRead.xAxis.categories = categories;
                obj_fs_line_Mgs_DiskRead.yAxis.title.text = 'KB';
                obj_fs_line_Mgs_DiskRead.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_fs_line_Mgs_DiskRead);
        });
}

/*****************************************************************************/
// All MDS/MGS Disk Write - Line Chart
/*****************************************************************************/

load_fsPageLine_Mgs_DiskWrite = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
        var optionData = [],categories = [];
        obj_fs_line_Mgs_DiskWrite = fs_lineOptions_Mgs_DiskWrite;
        obj_fs_line_Mgs_DiskWrite.title.text = "Disk Write";
        obj_fs_line_Mgs_DiskWrite.chart.renderTo = "fs_mgsavgWriteDiv";
        $.post("/api/gettargetwrites/",{datafunction: dataFunction, endtime: eDate, targetname: "", hostname: fsName, starttime: sDate})
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
		          obj_fs_line_Mgs_DiskWrite.series[count] = {
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
                 obj_fs_line_Mgs_DiskWrite.series[count] = { name: ostName, data: optionData };
		       }
       })
       .error(function(event) {
             // Display of appropriate error message
       })
       .complete(function(event){
                obj_fs_line_Mgs_DiskWrite.xAxis.categories = categories;
                obj_fs_line_Mgs_DiskWrite.yAxis.title.text = 'KB';
                obj_fs_line_Mgs_DiskWrite.xAxis.labels = {
                    rotation: 310,
                    step: 2
                }
                chart = new Highcharts.Chart(obj_fs_line_Mgs_DiskWrite);
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
