//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

function LoadFSGraph_EditFS(filesystem)
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
 
  obj_ost_pie_space = JSON.parse(JSON.stringify(chartConfig_Pie_DB));
  obj_ost_pie_space.title.text = null;
  obj_ost_pie_space.chart.renderTo = "editfs_space_usage";
  
  var free=0,used=0;
  free = Math.round(((filesystem.bytes_free)/(filesystem.bytes_total))*100);
  used = Math.round(100 - free);
  var freeData = [],usedData = [];
  freeData.push(free);
  usedData.push(used);

  obj_ost_pie_space.series = [{
  type: 'pie',
  name: '',
  data: [
     ['Free',    free],
     ['Used',    used]
    ]
  }];
  chart = new Highcharts.Chart(obj_ost_pie_space);

  obj_ost_pie_inode = JSON.parse(JSON.stringify(chartConfig_Pie_DB));
  obj_ost_pie_inode.title.text = null;
  obj_ost_pie_inode.chart.renderTo = "editfs_inode_usage";

  var free=0,used=0;
  free = Math.round(((filesystem.files_free)/(filesystem.files_total))*100);
  used = Math.round(100 - free);

  var freeFilesData = [],totalFilesData = [];
  freeFilesData.push(free);
  totalFilesData.push(used);

  obj_ost_pie_inode.series = [{
  type: 'pie',
  name: '',
  data: [
     ['Free',    free],
     ['Used',    used]
   ]
  }];
  chart = new Highcharts.Chart(obj_ost_pie_inode);
}
