	var chart;
	$(document).ready(function() {
	chart = new Highcharts.Chart({
		chart: {
			renderTo: 'fs_container2',
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
			renderTo: 'fs_container3',
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
		    renderTo: 'fs_avgCPUDiv',
			marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
		},
	    defaultSeriesType: 'line',
	    marginRight: 0,
	    marginBottom: 25
	},
	title: {
	    text: 'CPU Usage',
	    x: -20,
		style: {
			fontSize: '12px'
		},
	},
	xAxis: {
	    categories: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
	},
	yAxis: {
	    title: {
	        text: '%'
	    },
	    plotLines: [{
	        value: 0,
	        width: 1,
	        color: '#808080'
	    }]
	},
	tooltip: {
	    formatter: function() {
	            return '<b>'+ this.series.name +'</b><br/>'+
	            this.x +': '+ this.y +'';
	    }
	},
	legend: {
	    layout: 'vertical',
	    align: 'right',
	    verticalAlign: 'top',
	    x: 0,
	    y: 100,
	    borderWidth: 0
	},
	series: [{
	    name: 'MDT',
	    data: [10, 20, 30, 30, 30, 30, 30, 32, 32, 32]
	}]
	});
	
	chart = new Highcharts.Chart({
	chart: {
	    renderTo: 'fs_avgMemoryDiv',
		marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
		},
	    defaultSeriesType: 'line',
	    marginRight: 0,
	    marginBottom: 25
	},
	title: {
	    text: 'Memory Utilization',
	    x: -20,
		style: {
			fontSize: '12px'
		},
	},
	xAxis: {
	    categories: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
	},
	yAxis: {
	    title: {
	        text: '%'
	    },
	    plotLines: [{
	        value: 0,
	        width: 1,
	        color: '#808080'
	    }]
	},
	tooltip: {
	    formatter: function() {
	            return '<b>'+ this.series.name +'</b><br/>'+
	            this.x +': '+ this.y +'';
	    }
	},
	legend: {
	    layout: 'vertical',
	    align: 'right',
	    verticalAlign: 'top',
	    x: 0,
	    y: 100,
	    borderWidth: 0
	},
	series: [{
	    name: 'MDT',
	    data: [30, 30, 30, 30, 30, 25, 25, 25, 25, 25]
	}]
	});
	chart = new Highcharts.Chart({
	    chart: {
	           renderTo: 'fs_avgReadDiv',
			   marginLeft: '50',
				width: '250',
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
	           x: -20,
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
	                 renderTo: 'fs_avgWriteDiv',
					 marginLeft: '50',
				width: '250',
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
	                x: -20,
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
	
	chart = new Highcharts.Chart({
	chart: {
	    renderTo: 'fs_mgsavgCPUDiv',
		marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
		},
	    defaultSeriesType: 'line',
	    marginRight: 0,
	    marginBottom: 25
	},
	title: {
	    text: 'CPU Usage',
	    x: -20,
		style: {
			fontSize: '12px'
		},
	},
	xAxis: {
	    categories: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
	},
	yAxis: {
	    title: {
	        text: '%'
	    },
	    plotLines: [{
	        value: 0,
	        width: 1,
	        color: '#808080'
	    }]
	},
	tooltip: {
	    formatter: function() {
	            return '<b>'+ this.series.name +'</b><br/>'+
	            this.x +': '+ this.y +'';
	    }
	},
	legend: {
	    layout: 'vertical',
	    align: 'right',
	    verticalAlign: 'top',
	    x: 0,
	    y: 100,
	    borderWidth: 0
	},
	series: [{
	    name: 'MDT',
	    data: [10, 4, 8, 15, 13, 9, 12, 10, 18, 16]
	}]
	});
	chart = new Highcharts.Chart({
		chart: {
		    renderTo: 'fs_mgsavgMemoryDiv',
			marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
		},
		    defaultSeriesType: 'line',
		    marginRight: 0,
		    marginBottom: 25
		},
		title: {
		    text: 'Memory Utilization',
		    x: -20,
		style: {
			fontSize: '12px'
		},
		},
		xAxis: {
		    categories: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
		},
		yAxis: {
		    title: {
		        text: '%'
		    },
		    plotLines: [{
		        value: 0,
		        width: 1,
		        color: '#808080'
		    }]
		},
		tooltip: {
		    formatter: function() {
		            return '<b>'+ this.series.name +'</b><br/>'+
		            this.x +': '+ this.y +'';
		    }
		},
		legend: {
		    layout: 'vertical',
		    align: 'right',
		    verticalAlign: 'top',
		    x: 0,
		    y: 100,
		    borderWidth: 0
		},
		series: [{
		    name: 'MDT',
			    data: [10, 20, 22, 25, 8, 9, 30, 35, 20, 20]
			}]
			});
	
	chart = new Highcharts.Chart({
	chart: {
	    renderTo: 'fs_mgsavgReadDiv',
		marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
		},
	defaultSeriesType: 'line',
	    marginRight: 0,
	    marginBottom: 25
	},
	title: {
	    text: 'Avg MDT Disk Read',
	x: -20,
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
	plotLines: [{
	    value: 0,
	    width: 1,
	    color: '#808080'
	    }]
	},
	tooltip: {
	    formatter: function() {
	            return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	legend: {
	    layout: 'vertical',
	align: 'right',
	verticalAlign: 'top',
	    x: 0,
	    y: 100,
	    borderWidth: 0
	},
	series: [{
	    name: 'OSS1',
	    data: [6.0, 6.1, 6.1, 6.1, 6.2, 6.2, 6.2, 6.4, 6.4, 6.4]
	}, {
	    name: 'OSS2',
	    data: [3.0, 3.1, 3.2, 3.1, 3.1, 3.2, 3.1, 3.1, 3.1, 3.1]
	}]
	});
	
	chart = new Highcharts.Chart({
	chart: {
	    renderTo: 'fs_mgsavgWriteDiv',
		marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
		},
	defaultSeriesType: 'line',
	    marginRight: 0,
	    marginBottom: 25
	},
	title: {
	    text: 'Avg MDT Disk Write',
	x: -20,
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
	plotLines: [{
	    value: 0,
	    width: 1,
	    color: '#808080'
	    }]
	},
	tooltip: {
	    formatter: function() {
	            return '<b>'+ this.series.name +'</b><br/>'+
	        this.x +': '+ this.y +'';
	    }
	},
	legend: {
	    layout: 'vertical',
	align: 'right',
	verticalAlign: 'top',
	    x: 0,
	    y: 100,
	    borderWidth: 0
	},
	series: [{
	    name: 'OSS1',
	    data: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
	}, {
	    name: 'OSS2',
	    data: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
	}]
	});
});
