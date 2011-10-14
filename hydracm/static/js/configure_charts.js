$(document).ready(function() {
/*******************************************************************************/
var chartConfig_Pie_DB = 
{
    chart:{
    renderTo: '',
    marginLeft: '50',
	width: '180',
	height: '170',
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
	     pie:{allowPointSelect: true,cursor: 'pointer',showInLegend: true,center:['40%','60%'],size: '100%',dataLabels:{enabled: false,color: '#000000',connectorColor: '#000000'}}
	 },
	 series: []
};

/*****************************************************************************/
// Function for free INodes	- Pie Chart
// Param - File System name, start date, end date, datafunction (average/min/max)
// Return - Returns the graph plotted in container
/*****************************************************************************/

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
           obj_db_Pie_INodes_Data.chart.renderTo = "editfs_container3";       
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
	 
/*****************************************************************************/
// Function for space usage for all file systems	- Pie Chart
// Param - File System name, start date, end date, datafunction (average/min/max)
// Return - Returns the graph plotted in container
/*****************************************************************************/
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
            obj_db_Pie_Space_Data.chart.renderTo = "editfs_container2";
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
} );