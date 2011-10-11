/**************************************************************************/
//File Name - custome_ost.js
//Description - Contains function to plot pie, line and bar charts on OST Screen
//Functions - 
//---------------------Chart Configurations function-----------------------
//	1) pieDataOptions_OST - Pie chart configuration for space usage.
//	2) pieDataOptions_Inode_OST - Pie chart configuration for Inode usgae.
//	3) lineDataOptions_ost_disk_read - Line Chart configuration for disk read.
//	4) lineDataOptions_ost_disk_write - Line chart configuration for disk write.
//---------------------Data Loaders function-------------------------------
//	1) OST_Pie_Space_Data(fsName)
//	2) OST_Pie_Inode_Data(fsName, sDate, eDate, dataFunction)
//	3) OST_Line_DiskRead_Data(fsName, sDate, eDate, dataFunction,isZoom)
//	4) OST_Line_DiskWrite_Data(fsName, sDate, eDate, dataFunction,isZoom)
/******************************************************************************/
//for OST graph File system space usage
var ChartConfig_OST_Space = 
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

//for OST graph File system inode usage
var ChartConfig_OST_Inode =
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


//For OSS Disk Read
var ChartConfig_Line_OST_DiskRead=
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '500',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 35,
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
var ChartConfig_Line_OST_DiskWrite=
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '500',
    height: '200',
	style:{ width:'100%',  height:'210', position: 'inherit' },
    defaultSeriesType: 'line',
    marginRight: 0,
    marginBottom: 35,
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
// Function for OST for file system space
// Param - File System Name
// Return - Returns the graph plotted in container
/*****************************************************************************/
OST_Pie_Space_Data = function(fsName)
{
        var free=0,used=0;
		obj_ost_pie_space = ChartConfig_OST_Space;
        obj_ost_pie_space.title.text= fsName + " Space Usage";
        obj_ost_pie_space.chart.renderTo = "ost_container2";		
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
	    obj_ost_pie_space.series = [{
				type: 'pie',
				name: 'Browser share',
				data: [
					['Free',    free],
					['Used',    used]
					]
				}];
		        chart = new Highcharts.Chart(obj_ost_pie_space);
		});
}	

	
/*****************************************************************************/
// Function for OST for inode
// Param - File System Name
// Return - Returns the graph plotted in container
/*****************************************************************************/
OST_Pie_Inode_Data = function(fsName, sDate, eDate, dataFunction) //250
{
        var free=0,used=0;
		obj_ost_pie_inode = ChartConfig_OST_Inode;
        obj_ost_pie_inode.title.text= fsName + " - Files vs Free Inodes";
        obj_ost_pie_inode.chart.renderTo = "ost_container3";		
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
	    obj_ost_pie_inode.series = [{
				type: 'pie',
				name: 'Browser share',
				data: [
					['Free',    free],
					['Used',    used]
					]
				}];
		        chart = new Highcharts.Chart(obj_ost_pie_inode);
		});
}


/*****************************************************************************/
// Function for Line chart Disk read
// Param - File System name, start date, end date, datafunction (avergae/"")
// Return - Returns the graph plotted in container
/*****************************************************************************/	
OST_Line_DiskRead_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
		var seriesUpdated = 0;
        obj_ost_line_diskread = ChartConfig_Line_OST_DiskRead;
        obj_ost_line_diskread.title.text = "Disk Read";
        obj_ost_line_diskread.chart.renderTo = "ost_avgReadDiv";
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
          obj_ost_line_diskread.series[count] = {
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
			   obj_ost_line_diskread.series[0] = {
                name: ossName,
                data: optionData
                   };
		   }
		   else
		   {
			   obj_ost_line_diskread.series[count] = {
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
                obj_ost_line_diskread.xAxis.categories = categories;
                obj_ost_line_diskread.yAxis.title.text = 'KB';
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_ost_line_diskread);
        		}
                chart = new Highcharts.Chart(obj_ost_line_diskread);
        });
}

/*****************************************************************************/
// Function for Disk Read
// Param - File System name, start date, end date, datafunction (avergae/"")
// Return - Returns the graph plotted in container
/*****************************************************************************/	
OST_Line_DiskWrite_Data = function(fsName, sDate, eDate, dataFunction, isZoom)
 {
        var count = 0;
        var optionData = [],categories = [];
		var seriesUpdated = 0;
        obj_ost_line_diskwrite = ChartConfig_Line_OST_DiskWrite;
        obj_ost_line_diskwrite.title.text = "Disk Write";
        obj_ost_line_diskwrite.chart.renderTo = "ost_avgWriteDiv";
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
          obj_ost_line_diskwrite.series[count] = {
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
			   obj_ost_line_diskwrite.series[0] = {
                name: ossName,
                data: optionData
                   };
		   }
		   else
		   {
			   obj_ost_line_diskwrite.series[count] = {
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
                obj_ost_line_diskwrite.xAxis.categories = categories;
                obj_ost_line_diskwrite.yAxis.title.text = 'KB';
                if(isZoom == 'true')
        		{
                	renderZoomDialog(obj_ost_line_diskwrite);
        		}
                chart = new Highcharts.Chart(obj_ost_line_diskwrite);
        });
}   
