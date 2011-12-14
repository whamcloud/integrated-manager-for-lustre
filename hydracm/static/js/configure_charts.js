function LoadFSGraph_EditFS(fs_id)
{
  var spaceUsageFetchMatric = "kbytestotal kbytesfree filestotal filesfree";
  var fs_Pie_Space_Data_Api_Url = "get_fs_stats_for_targets/";
  /*******************************************************************************/
  var chartConfig_Pie_DB = 
  {
    chart:{
      renderTo: '',
      width: '100',
      height: '100',
      backgroundColor: null,
      plotShadow: false,
      borderWidth: 0,

    },
    colors: [
      '#A6C56D', 
      '#C76560'
       ],
    zoomType: 'xy',
    title: {},
    xAxis:{ categories: [], text: '' },
    yAxis:{ title:{text:''}, plotLines: [{value: 0,width: 1, color: '#808080' }]},
    credits:{ enabled:false },
    legend: {enabled: false},
    tooltip:
    {
      formatter: function() 
        {
          return '<b>'+ this.point.name +'</b>: '+ this.y +' %';
        }
     },
     plotOptions:
     {
       pie:{allowPointSelect: true,cursor: 'pointer',showInLegend: true, dataLabels: {enabled: false}}
     },
     series: []
  };
 
  var free=0,used=0;
  var freeData = [],usedData = [];
  obj_ost_pie_space = JSON.parse(JSON.stringify(chartConfig_Pie_DB));
  obj_ost_pie_space.title.text = null;
  obj_ost_pie_space.chart.renderTo = "editfs_space_usage";
  
  var api_params = {
      targetkind: 'OST', datafunction: 'Average', fetchmetrics: spaceUsageFetchMatric, 
      starttime: "", filesystem_id: fs_id, endtime: ""
  };
  
  invoke_api_call(api_post, fs_Pie_Space_Data_Api_Url, api_params, 
  success_callback = function(data)
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

    obj_ost_pie_space.series = [{
    type: 'pie',
    name: '',
    data: [
       ['Free',    free],
       ['Used',    used]
      ]
    }];
    chart = new Highcharts.Chart(obj_ost_pie_space);
  },
  error_callback = function(data){
  });

  var free=0,used=0;
  var freeFilesData = [],totalFilesData = [];
  obj_ost_pie_inode = JSON.parse(JSON.stringify(chartConfig_Pie_DB));
  obj_ost_pie_inode.title.text = null;
  obj_ost_pie_inode.chart.renderTo = "editfs_inode_usage";

  var api_params = {
      targetkind: 'MDT', datafunction: 'Average', fetchmetrics: spaceUsageFetchMatric, 
      starttime: "", filesystem_id: fs_id, endtime: ""
  };

  invoke_api_call(api_post, fs_Pie_Space_Data_Api_Url, api_params, 
  success_callback = function(data)
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

    obj_ost_pie_inode.series = [{
    type: 'pie',
    name: '',
    data: [
       ['Free',    free],
       ['Used',    used]
     ]
    }];
    chart = new Highcharts.Chart(obj_ost_pie_inode);
  },
  error_callback = function(data){
  });
}
