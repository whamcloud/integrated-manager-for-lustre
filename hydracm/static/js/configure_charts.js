	var chart;
	var pieDataOptions = {			// Preloaded options for pie charts
	chart: {
		renderTo: '',
		marginLeft: '50',
		width: '150',
		style: {
			width:'100%',
			height:'200px',
		},
		
		plotBackgroundColor: null,
		plotBorderWidth: null,
		plotShadow: false
	},
	title: {
		text: '',
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
			},
			
		}
	},
	series: []
	};
	
	$(document).ready(function() {
		
	pieDataOptions.title.text="All File System Space Usage";
	pieDataOptions.chart.renderTo = "capacity";
	pieDataOptions.series = [{
			type: 'pie',
			name: 'Browser share',
			data: [
				['Free',    80],
				['Used',    20]
				]
			}];
	chart = new Highcharts.Chart(pieDataOptions);					// All File System Space Usage
	
	pieDataOptions.title.text="All File System File Usage";
	pieDataOptions.chart.renderTo = "inodes";
	pieDataOptions.series = [{
		type: 'pie',
		name: 'Browser share',
		data: [
			['Free',40],
			['Used',60]
			]
		}];
	chart = new Highcharts.Chart(pieDataOptions);					// All File System File Usage
});
	
	