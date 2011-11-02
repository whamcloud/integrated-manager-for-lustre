function LoadFSGraph_EditFS(fs_id)
{
  var spaceUsageFetchMatric = "kbytestotal kbytesfree filestotal filesfree";
  var fs_Pie_Space_Data_Api_Url = "/api/get_fs_stats_for_targets/";
  /*******************************************************************************/
  var chartConfig_Pie_DB = 
  {
    chart:{
    renderTo: '',
    marginLeft: '50',
    width: '180',
    height: '170',
    backgroundColor: '#f9f9ff',
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
       pie:{allowPointSelect: true,cursor: 'pointer',showInLegend: true,center:['40%','60%'],size: '100%',dataLabels:{enabled: false,color: '#000000',connectorColor: '#000000'}}
     },
     series: []
  };
 
  var free=0,used=0;
  var freeData = [],usedData = [];
  obj_ost_pie_space = JSON.parse(JSON.stringify(chartConfig_Pie_DB));
  obj_ost_pie_space.title.text= fs_id + " Space Usage";
  obj_ost_pie_space.chart.renderTo = "editfs_container2";
  $.post(fs_Pie_Space_Data_Api_Url,
    {targetkind: 'OST', datafunction: 'Average', fetchmetrics: spaceUsageFetchMatric, 
     starttime: "", filesystem_id: fs_id, endtime: ""})
    .success(function(data, textStatus, jqXHR) 
    {   
      if(data.success)
      {
        var response = data.response;
        var totalDiskSpace=0,totalFreeSpace=0;
        $.each(response, function(resKey, resValue) 
        {
          if(resValue.filesystem != undefined)
          {
            totalFreeSpace = resValue.kbytesfree/1024;
            totalDiskSpace = resValue.kbytestotal/1024;
            free = Math.round(((totalFreeSpace/1024)/(totalDiskSpace/1024))*100);
            used = Math.round(100 - free);
            freeData.push(free);
            usedData.push(used);
          }
        });
      }
    })
    .error(function(event) 
    {
        // Display of appropriate error message
    })
    .complete(function(event) 
    {
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
     
    var free=0,used=0;
    var freeFilesData = [],totalFilesData = [];
    obj_ost_pie_inode = JSON.parse(JSON.stringify(chartConfig_Pie_DB));
    obj_ost_pie_inode.title.text= fs_id + " - Files vs Free Files";
    obj_ost_pie_inode.chart.renderTo = "editfs_container3";  
    $.post(fs_Pie_Space_Data_Api_Url,
      {targetkind: 'MDT', datafunction: 'Average', fetchmetrics: spaceUsageFetchMatric, 
       starttime: "", filesystem_id: fs_id, endtime: ""})
    .success(function(data, textStatus, jqXHR) 
    {   
      if(data.success)
      {
        var response = data.response;
        var totalFiles=0,totalFreeFiles=0;
        $.each(response, function(resKey, resValue) 
        {
          if(resValue.filesystem != undefined)
          {
            totalFiles = resValue.filesfree;
            totalFreeFiles = resValue.filestotal;
            free = Math.round(((totalFiles)/(totalFreeFiles))*100);
            used = Math.round(100 - free);
            freeFilesData.push(free);
            totalFilesData.push(used);
          }   
        });
      }
   })
   .error(function(event) 
   {
      // Display of appropriate error message
   })
   .complete(function(event) 
   {
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