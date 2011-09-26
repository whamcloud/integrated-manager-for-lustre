	var chart;
	$(document).ready(function() {
		chart = new Highcharts.Chart({
			chart: {
				renderTo: 'container',
				marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
		},
	
	},
	title: {
		text: 'File System Used Vs Free Capacity',
		style: {
			fontSize: '12px'
		},
	},
	xAxis: {
		categories: ['Used', 'Free']
	},
	yAxis: {
		title: {
			text: 'Usage (%)'
		},
	},
	tooltip: {
		formatter: function() {
			var s;
			if (this.point.name) { // the pie chart
				s = ''+
					this.point.name +': '+ this.y +' fruits';
			} else {
				s = ''+
					this.x  +': '+ this.y;
			}
			return s;
		}
	},
	labels: {
		items: [{
			html: '',
			style: {
				left: '40px',
				top: '8px',
				color: 'black'				
			}
		}]
	},
	series: [{
		type: 'column',
		name: 'File System Used',
		data: [80, 20]
	}, {
		type: 'column',
		name: 'Free Capacity',
			data: [60, 40]
		}]
	});
	chart = new Highcharts.Chart({
		chart: {
			renderTo: 'container1',
			marginLeft: '50',
			width: '250',
		style: {
			width:'100%',
			height:'200px',
		}
	},
	title: {
		text: 'File System Used Vs Free Capacity',
		style: {
			fontSize: '12px'
		},
	},
	xAxis: {
		categories: ['Used', 'Free']
	},
	yAxis: {
		title: {
			text: 'Usage (%)'
		},
	},
	tooltip: {
		formatter: function() {
			var s;
			if (this.point.name) { // the pie chart
				s = ''+
					this.point.name +': '+ this.y +' fruits';
			} else {
				s = ''+
					this.x  +': '+ this.y;
			}
			return s;
		}
	},
	labels: {
		items: [{
			html: '',
			style: {
				left: '40px',
				top: '8px',
				color: 'black'				
			}
		}]
	},
	series: [{
		type: 'column',
		name: 'File System Used',
		data: [80, 20]
	}, {
		type: 'column',
		name: 'Free Capacity',
			data: [60, 40]
		}]
	});
	chart = new Highcharts.Chart({
		chart: {
			renderTo: 'container2',
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
			renderTo: 'container3',
			marginLeft: '30',
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
		    renderTo: 'avgCPUDiv',
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
	    renderTo: 'avgMemoryDiv',
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
		style: {
			fontSize: '12px'
		},
	    x: -20 //center
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
	           renderTo: 'avgReadDiv',
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
			   style: {
			fontSize: '12px'
		},
	           x: -20 //center
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
	                 renderTo: 'avgWriteDiv',
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
					style: {
			fontSize: '12px'
		},
	                x: -20 //center
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
	    renderTo: 'mgsavgCPUDiv',
		marginLeft: '50',
				width: '250',
				height:'200',
		style: {
			width:'100%',
			height:'200px',
			position:'inherit',
		},
	    defaultSeriesType: 'line',
	    marginRight: 0,
	    marginBottom: 25
	},
	title: {
	    text: 'CPU Usage',
		style: {
			fontSize: '12px'
		},
	    x: -20 //center
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
		    renderTo: 'mgsavgMemoryDiv',
			marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
			position:'inherit',
		},
		    defaultSeriesType: 'line',
		},
		title: {
		    text: 'Memory Utilization',
			style: {
			fontSize: '12px'
		},
		    x: -20 //center
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
	    renderTo: 'mgsavgReadDiv',
		marginLeft: '50',
		width: '250',
		style: {
			width:'100%',
			height:'200px',
			position:'inherit',
		},
	defaultSeriesType: 'line',
	    marginRight: 0,
	    marginBottom: 25
	},
	title: {
	    text: 'Avg MDT Disk Read',
		style: {
			fontSize: '12px'
		},
	x: -20 //center
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
	    renderTo: 'mgsavgWriteDiv',
		 marginLeft: '50',
				width: '250',
		style: {
			width:'100%',
			height:'200px',
			position:'inherit',
		},
		defaultSeriesType: 'line',
	  
	},
	title: {
	    text: 'Avg MDT Disk Write',
		style: {
			fontSize: '12px'
		},
	x: -20 //center
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


	
	
	
	$('.text').mouseover(function() {
		$(this).css("border","0px solid #444444");
	});
	$('.text').mouseout(function() {
		$(this).css("border","0px solid black");
	});
	
	$("#breadCrumb0").jBreadCrumb();
	
	$("#plusImg").click(function(){
		$(".panel").toggle("slow");
		$("#plusImg").hide();$("#minusImg").show();
		$(this).toggleClass("active");
		return false;
	});
	
	$("#minusImg").click(function(){
		$(".panel").toggle("slow");
		$(this).toggleClass("active");
		$("#minusImg").hide();$("#plusImg").show();
		return false;
	});
	
	$("#alertAnchor").click(function(){
		$("#alertsDiv").toggle("slideUp");
		$("#alertAnchor").css("color",'red');
		$("#eventsDiv").hide();
		$("#eventsAnchor").css("color",'#7A848B');
		$("#jobsAnchor").css("color",'#7A848B');
		$("#jobsDiv").hide();
	});
	$("#eventsAnchor").click(function(){
		$("#eventsDiv").toggle("slideUp");
		$("#eventsAnchor").css("color",'#0040FF');
		$("#alertsDiv").hide();
		$("#alertAnchor").css("color",'#7A848B');
		$("#jobsDiv").hide();
		$("#jobsAnchor").css("color",'#7A848B');
	});
	$("#jobsAnchor").click(function(){
		$("#jobsDiv").toggle("slideUp");
		$("#jobsAnchor").css("color",'green');
		$("#alertsDiv").hide();
		$("#alertAnchor").css("color",'#7A848B');
		$("#eventsDiv").hide();
		$("#eventsAnchor").css("color",'#7A848B');
	});

	
	$("#intervalSelect").change(function(){
		var intervalValue = $(this).val();
		var unitSelectOptions = "";
		if(intervalValue == "")
		{
			unitSelectOptions = "<option value=''>Select</option>";
		}
		else if(intervalValue == "hour")
		{
			unitSelectOptions = getUnitSelectOptions(24);
		}
		else if(intervalValue == "day")
		{
			unitSelectOptions = getUnitSelectOptions(32);
		}
		else if(intervalValue == "week")
		{
			unitSelectOptions = getUnitSelectOptions(5);
		}
		else if(intervalValue == "month")
		{
			unitSelectOptions = getUnitSelectOptions(13);
		}
		$("#unitSelect").html(unitSelectOptions);
	});
	
	function getUnitSelectOptions(countNumber)
	{
		var unitSelectOptions="<option value=''>Select</option>";
		for(var i=1; i<countNumber; i++)
		{
			unitSelectOptions = unitSelectOptions + "<option value="+i+">"+i+"</option>";
		}
		return unitSelectOptions;
	}
	
	$("#fsSelect").change(function(){
		if($(this).val()!="")
		{
			 $('#dashboardDiv').hide();$('#ossInfoDiv').hide();$('#ostInfoDiv').hide();
			 $('#fileSystemDiv').slideDown("slow");
			 var breadCrumbHtml = "<ul>"+
			 "<li><a href='/dashboard'>Home</a></li>"+
			 "<li><a href='/dashboard'>All FileSystems</a></li>"+
			 "<li>"+$('#fsSelect :selected').text()+"</li>"+
			 "<li>"+
             "<select id='ossSelect'>"+
             "<option value=''>Select OSS</option>"+

		     $.get("/api/listservers") 
		    .success(function(data, textStatus, jqXHR) {
		        $.each(data, function(key, val) {
		            if(key=='success' && val == true)
		            {
		                $.each(data, function(key1, val1) {
		                if(key1=='response')
		                {
		                   $.each(val1, function(resKey, resValue) 
		                   {
		                        if(resValue.kind=='OSS' || resValue.kind.indexOf('OSS')>0)
		                        {
		                          breadCrumbHtml  =  breadCrumbHtml + "<option value="+resValue.host_address+">"+resValue.host_address+"</option>";
		                        }
		                   });
		                }
		                });
		            }
		        });
		    })
		    .error(function(event) {
		        //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
		    })
		    .complete(function(event){
		         breadCrumbHtml = breadCrumbHtml +
	             "</select>"+
	             "</li>"+
	             "</ul>";
	             $("#breadCrumb1").html(breadCrumbHtml);
	             $("#breadCrumb1").jBreadCrumb();
		    });
		}
    });         
	
	$("#ossSelect").live('change', function (){
		if($(this).val()!="")
		{
			$('#dashboardDiv').hide();$('#fileSystemDiv').hide();$('#ostInfoDiv').hide();
			$('#ossInfoDiv').slideDown("slow");
			 var breadCrumbHtml = "<ul>"+
			 "<li><a href='/dashboard'>Home</a></li>"+
			 "<li><a href='/dashboard'>All FileSystems</a></li>"+
			 "<li><a href='#' onclick='showFSInfo()'>"+$('#fsSelect :selected').text()+"</a></li>"+
			 "<li>"+$('#ossSelect :selected').text()+"</li>"+
             "<li>"+
             "<select id='ostSelect'>"+
             "<option value=''>Select OST</option>";
             
			 $.post("/api/getvolumes/",{filesystem:"neofs01"}) 
			    .success(function(data, textStatus, jqXHR) {
			        $.each(data, function(key, val) {
			            if(key=='success' && val == true)
			            {
			                $.each(data, function(key1, val1) {
			                if(key1=='response')
			                {
			                   $.each(val1, function(resKey, resValue) 
			                   {
			                        if(resValue.kind=='OST')
			                        {
			                          breadCrumbHtml  =  breadCrumbHtml + "<option value="+resValue.name+">"+resValue.name+"</option>";
			                        }
			                   });
			                }
			                });
			            }
			        });
			    })
			    .error(function(event) {
			        //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
			    })
			    .complete(function(event){
			    	breadCrumbHtml = breadCrumbHtml +      	
		            "</select>"+
		            "</li>"+
		            "</ul>";
		         $("#breadCrumb2").html(breadCrumbHtml);
				 $("#breadCrumb2").jBreadCrumb();
			    });
        }
    });
	
	$("#ostSelect").live('change', function (){
		if($(this).val()!="")
		{
			$('#dashboardDiv').hide();$('#fileSystemDiv').hide();$('#ossInfoDiv').hide();
			$('#ostInfoDiv').slideDown("slow");
			 var breadCrumbHtml = "<ul>"+
			 "<li><a href='/dashboard'>Home</a></li>"+
			 "<li><a href='/dashboard'>All FileSystems</a></li>"+
			 "<li><a href='#' onclick='showFSInfo()'>"+$('#fsSelect :selected').text()+"</a></li>"+
			 "<li><a href='#' onclick='showOSSInfo()'>"+$('#ossSelect :selected').text()+"</a></li>"+
			 "<li>"+$('#ostSelect :selected').text()+"</li>"+
         "</ul>";
         $("#breadCrumb3").html(breadCrumbHtml);
		 $("#breadCrumb3").jBreadCrumb();
		}
    });
	
	$(".tab_content").hide(); //Hide all content
	$("ul.tabs li:first").addClass("active").show(); //Activate first tab
	$(".tab_content:first").show(); //Show first tab content

	//On Click Event
	$("ul.tabs li").click(function() {

		$("ul.tabs li").removeClass("active"); //Remove any "active" class
		$(this).addClass("active"); //Add "active" class to selected tab
		$(".tab_content").hide(); //Hide all tab content

		var activeTab = $(this).find("a").attr("href"); //Find the href attribute value to identify the active tab + content
		$(activeTab).fadeIn(); //Fade in the active ID content
		return false;
	});

	// Dialog			
	$('#alerts_dialog').dialog({
		autoOpen: false,
		width: 800,
		height:400,
		show: "clip",
		modal: true,
		buttons: {
			"Ok": function() { 
				$(this).dialog("close"); 
			}/*, 
			"Cancel": function() { 
				$(this).dialog("close"); 
			} */
		}
	});
	// Dialog			
	$('#events_dialog').dialog({
		autoOpen: false,
		width: 800,
		height:400,
		show: "clip",
		modal: true,
		buttons: {
			"Ok": function() { 
				$(this).dialog("close"); 
			}/*, 
			"Cancel": function() { 
				$(this).dialog("close"); 
			} */
		}
	});
	
	// Dialog Link
	$('input[name=alertsPopUpBtn]').click(function(){
		$('#alerts_dialog').dialog('open');
		return false;
	});
	$('input[name=eventsPopUpBtn]').click(function(){
		$('#events_dialog').dialog('open');
		return false;
	});
	
	$('input[name=alertsPopUpBtn]').hover(function() {
		$(this).css('cursor','pointer');
	}, function() {
		$(this).css('cursor','auto');
	});
	$('input[name=eventsPopUpBtn]').hover(function() {
		$(this).css('cursor','pointer');
	}, function() {
		$(this).css('cursor','auto');
	});
	
	/********* URL's start*****************/
	var getVolumes = "";
	
	/********* URL's end*****************/
});
