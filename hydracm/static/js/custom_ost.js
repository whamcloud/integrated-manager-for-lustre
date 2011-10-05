//for OST graph File system space usage
var pieDataOptions_OST = 
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
var pieDataOptions_Inode_OST = 
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
var lineDataOptions_ost_disk_read= 
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '500',
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

//For OSS Disk Read
var lineDataOptions_ost_disk_write= 
{
	chart:{
    renderTo: '',
    marginLeft: '50',
	width: '500',
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
// Function for OST for file system space
// Param - File System Name
// Return - Returns the graph plotted in container
/*****************************************************************************/
load_OSSPagePie_disk_OST = function(fsName)
{
        var free=0,used=0;
		obj_db_OSSPagePie = pieDataOptions_OST;
        obj_db_OSSPagePie.title.text= fsName + " Space Usage";
        obj_db_OSSPagePie.chart.renderTo = "ost_container2";		
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
	    obj_db_OSSPagePie.series = [{
				type: 'pie',
				name: 'Browser share',
				data: [
					['Free',    free],
					['Used',    used]
					]
				}];
		        chart = new Highcharts.Chart(obj_db_OSSPagePie);
		});
}	

	
/*****************************************************************************/
// Function for OST for inode
// Param - File System Name
// Return - Returns the graph plotted in container
/*****************************************************************************/
load_INodePagePie_disk_OST = function(fsName, sDate, eDate, dataFunction)
{
        var free=0,used=0;
		obj_db_INodePagePie = pieDataOptions_Inode_OST;
        obj_db_INodePagePie.title.text= fsName + " - Files vs Free Inodes";
        obj_db_INodePagePie.chart.renderTo = "ost_container3";		
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
	    obj_db_INodePagePie.series = [{
				type: 'pie',
				name: 'Browser share',
				data: [
					['Free',    free],
					['Used',    used]
					]
				}];
		        chart = new Highcharts.Chart(obj_db_INodePagePie);
		});
}


/*****************************************************************************/
// Function for Line chart Disk read
// Param - File System name, start date, end date, datafunction (avergae/"")
// Return - Returns the graph plotted in container
/*****************************************************************************/	
load_LineChart_DiskRead_OST = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
        var optionData = [],categories = [];
		var seriesUpdated = 0;
        obj_gn_line_DiskRead = lineDataOptions_ost_disk_read;
        obj_gn_line_DiskRead.title.text = "Disk Read";
        obj_gn_line_DiskRead.chart.renderTo = "ost_avgReadDiv";
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
          obj_gn_line_DiskRead.series[count] = {
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
			   obj_gn_line_DiskRead.series[0] = {
                name: ossName,
                data: optionData
                   };
		   }
		   else
		   {
			   obj_gn_line_DiskRead.series[count] = {
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
                obj_gn_line_DiskRead.xAxis.categories = categories;
                obj_gn_line_DiskRead.yAxis.title.text = 'KB';
                obj_gn_line_DiskRead.xAxis.labels = {
                    rotation: 310,
                    step: 10
                }
                chart = new Highcharts.Chart(obj_gn_line_DiskRead);
        });
}

/*****************************************************************************/
// Function for Disk Read
// Param - File System name, start date, end date, datafunction (avergae/"")
// Return - Returns the graph plotted in container
/*****************************************************************************/	
loadLineChart_DiskWrite_OST = function(fsName, sDate, eDate, dataFunction)
 {
        var count = 0;
        var optionData = [],categories = [];
		var seriesUpdated = 0;
        obj_gn_line_DiskWrite = lineDataOptions_ost_disk_write;
        obj_gn_line_DiskWrite.title.text = "Disk Write";
        obj_gn_line_DiskWrite.chart.renderTo = "ost_avgWriteDiv";
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
          obj_gn_line_DiskWrite.series[count] = {
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
			   obj_gn_line_DiskWrite.series[0] = {
                name: ossName,
                data: optionData
                   };
		   }
		   else
		   {
			   obj_gn_line_DiskWrite.series[count] = {
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
                obj_gn_line_DiskWrite.xAxis.categories = categories;
                obj_gn_line_DiskWrite.yAxis.title.text = 'KB';
                obj_gn_line_DiskWrite.xAxis.labels = {
                    rotation: 310,
                    step: 10
                }
                chart = new Highcharts.Chart(obj_gn_line_DiskWrite);
        });
}   