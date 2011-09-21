	var chart;
	$(document).ready(function() {
	chart = new Highcharts.Chart({
		chart: {
			renderTo: 'ost_container2',
	marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
		},
		plotBackgroundColor: null,
		plotBorderWidth: null,
		plotShadow: false
	},
	title: {
		text: 'All File System Space Usage',
		style: {
			fontSize: '12px'
		},
	},
	tooltip: {
		formatter: function() {
			return '<b>'+ this.point.name +'</b>: '+ this.y +' %';
		}
	},
	plotOptions: {
		pie: {
			allowPointSelect: true,
			cursor: 'pointer',
			showInLegend: true,
			size: '100%',
	dataLabels: {
		enabled: false,
		color: '#000000',
		connectorColor: '#000000',
		formatter: function() {
			return '<b>'+ this.point.name +'</b>: '+ this.y +' %';
				}
			}
		}
	},
	series: [{
		type: 'pie',
	name: 'Browser share',
	data: [
		['Free',    80],
	['Used',    20]
			]
		}]
	});
	chart = new Highcharts.Chart({
		chart: {
			renderTo: 'ost_container3',
			marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
		},
		plotBackgroundColor: null,
		plotBorderWidth: null,
		plotShadow: false
	},
	title: {
		text: 'All File System File Usage',
		style: {
			fontSize: '12px'
		},
	},
	tooltip: {
		formatter: function() {
			return '<b>'+ this.point.name +'</b>: '+ this.y +' %';
		}
	},
	plotOptions: {
		pie: {
			allowPointSelect: true,
			cursor: 'pointer',
			showInLegend: true,
			size: '100%',
	dataLabels: {
		enabled: false,
		color: '#000000',
		connectorColor: '#000000',
		formatter: function() {
			return '<b>'+ this.point.name +'</b>: '+ this.y +' %';
				}
			}
		}
	},
	series: [{
		type: 'pie',
	name: 'Browser share',
	data: [
		['Free',40],
	['Used',60]
			]
		}]
	});
	
	chart = new Highcharts.Chart({
	    chart: {
	           renderTo: 'ost_avgReadDiv',
			   marginLeft: '50',
				width: '500',
		style: {
			width:'100%',
			height:'200px',
		},
	   defaultSeriesType: 'line',
	       marginRight: 0,
	       marginBottom: 25
	       },
	title: {
	       text: 'Avg Disk Read',
	   x: -20, //center
		style: {
			fontSize: '12px'
		},
	       },
	xAxis: {
	       categories: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
	       },
	yAxis: {
	        title: {
	               text: 'KB'
	           },
	   plotLines: [{value: 0,width: 1,color: '#808080'                                                                                                                                                                        }]                                                                                                                                                                                                                                                                                    },
	   legend: {
	            layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 100,borderWidth: 0
	   },
	   series: [{
	                name: 'FS1',
	        data: [7.0, 6.9, 9.5, 14.5, 18.2, 21.5, 25.2, 26.5, 15.5, 10.2]
	    }, {
	         name: 'FS2',
	                 data: [0.2, 0.8, 5.7, 11.3, 17.0, 22.0, 24.8, 24.1, 24.3, 12.2]
	            }]
	});
	
	chart = new Highcharts.Chart({
	         chart: {
	                 renderTo: 'ost_avgWriteDiv',
					 marginLeft: '50',
				width: '500',
		style: {
			width:'100%',
			height:'200px',
		},
	         defaultSeriesType: 'line',
	         marginRight: 0,
	         marginBottom: 25
	       },
	 title: {
	        text: 'Avg Disk Write',
	        x: -20, //center
			
		style: {
			fontSize: '12px'
		},
	},
	xAxis: {
	        categories: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
	},
	yAxis: {
	        title: {
	                text: 'KB'
	        },
	        plotLines: [{value: 0,width: 1,color: '#808080'                                                                                                                                                                        }]                                                                                                                                                                                                                                                                                    },
	legend: {
	        layout: 'vertical',align: 'right',verticalAlign: 'top',x: 0,y: 100,borderWidth: 0
	},
	series: [{
	        name: 'OSS1',
	        data: [8.0, 8.9, 9.5, 9.3, 9.3, 9.3, 8.7, 5.5, 5.2, 5.2]
	}, {
	name: 'OSS2',
		                data: [0.2, 0.8, 0.9, 0.9, 0.9, 0.5, 0.4, 0.6, 0.6, 0.6]
		        }]
		});
	});
		

