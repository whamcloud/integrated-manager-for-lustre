//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

function LoadFSGraph_EditFS(filesystem)
{
  var chartConfig_Pie_DB =
  {
    chart:{
      renderTo: '',
      width: '100',
      height: '100',
      backgroundColor: null,
      plotShadow: false,
      borderWidth: 0,
      animation: false
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
    tooltip: {enabled: false},
     plotOptions:
     {
       pie:{
         allowPointSelect: false,
         cursor: 'normal',
         showInLegend: true,
         dataLabels: {enabled: false},
         animation: false
       }
     },
     series: []
  };
 
  var obj_ost_pie_space = JSON.parse(JSON.stringify(chartConfig_Pie_DB));
  obj_ost_pie_space.title.text = null;
  obj_ost_pie_space.chart.renderTo = "editfs_space_usage";
  
  var free = Math.round(((filesystem.bytes_free)/(filesystem.bytes_total))*100);
  var used = Math.round(100 - free);
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

  new Highcharts.Chart(obj_ost_pie_space);

  var obj_ost_pie_inode = JSON.parse(JSON.stringify(chartConfig_Pie_DB));
  obj_ost_pie_inode.title.text = null;
  obj_ost_pie_inode.chart.renderTo = "editfs_inode_usage";

  var free = Math.round(((filesystem.files_free)/(filesystem.files_total))*100);
  var used = Math.round(100 - free);

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
  new Highcharts.Chart(obj_ost_pie_inode);
}
