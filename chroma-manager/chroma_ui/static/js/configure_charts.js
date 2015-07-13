//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


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
