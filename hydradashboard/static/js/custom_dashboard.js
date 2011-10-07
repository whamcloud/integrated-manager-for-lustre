/*****************************************************************************/
// Page Ready :: Load breadcrumbs for navigation
//            :: Bind events for breadcrumbs navigation  
//            :: Bind events for Jobs, Alerts and Events 
/*****************************************************************************/
$(document).ready(
function() 
{
/******************************************************************************/
// Function to load breadcrumb
/******************************************************************************/

load_breadcrumbs = function()
{		
    $("#breadCrumb0").jBreadCrumb();
}

/******************************************************************************/
// Events for controlling left panel
/******************************************************************************/
    $("#plusImg").click(
    function()
    {
        $(".panel").toggle("slow");
        $("#plusImg").hide();$("#minusImg").show();
        $(this).toggleClass("active");
        return false;
    });
		
		  $("#minusImg").click(
    function()
    {
			     $(".panel").toggle("slow");
     			$(this).toggleClass("active");
    	 		$("#minusImg").hide();$("#plusImg").show();
			     return false;
		  });
		
			$("#alertAnchor").click(function()
			{	
					$("#alertsDiv").toggle("slideUp");
					$("#alertAnchor").css("color",'red');
					$("#eventsDiv").hide();
					$("#eventsAnchor").css("color",'#7A848B');
					$("#jobsAnchor").css("color",'#7A848B');
					$("#jobsDiv").hide();
			});
	
			$("#eventsAnchor").click(function()
			{
					$("#eventsDiv").toggle("slideUp");
					$("#eventsAnchor").css("color",'#0040FF');
					$("#alertsDiv").hide();
					$("#alertAnchor").css("color",'#7A848B');
					$("#jobsDiv").hide();
					$("#jobsAnchor").css("color",'#7A848B');
			});
	
			$("#jobsAnchor").click(function()
			{
					$("#jobsDiv").toggle("slideUp");
					$("#jobsAnchor").css("color",'green');
					$("#alertsDiv").hide();
					$("#alertAnchor").css("color",'#7A848B');
					$("#eventsDiv").hide();
					$("#eventsAnchor").css("color",'#7A848B');
			});
	
/******************************************************************************/
// Function for showing time interval units
/******************************************************************************/
		
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

/******************************************************************************/
// Function to populate oss/mds/mgs list on selecting particular file system
/******************************************************************************/
		
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
	             "<option value=''>Select OSS</option>";

			     $.get("/api/listservers") 
			    .success(function(data, textStatus, jqXHR) {
			    	 if(data.success)
	                 {
	                     $.each(data.response, function(resKey, resValue)
	                     {
	                         if(resValue.kind=='OSS' || resValue.kind.indexOf('OSS')>0)
	                         {
	                            breadCrumbHtml  =  breadCrumbHtml + "<option value="+resValue.host_address+">"+resValue.host_address+"</option>";
	                         }
	                     });
	                 }
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
                 fs_Pie_Space_Data($('#fsSelect').val(),"","","","false");
                 fs_Pie_INodes_Data($('#fsSelect').val(),"","","","false");

                 fs_Line_CpuUsage_Data("average",$('#fsSelect').val(),"29-20-2011","29-20-2011","false");
                 fs_Line_MemoryUsage_Data("average",$('#fsSelect').val(),"29-20-2011","29-20-2011","false");
                 fs_Line_DiskRead_Data("average","29-20-2011",$('#fsSelect').val(),"29-20-2011","false");
                 fs_Line_DiskWrite_Data("average","29-20-2011",$('#fsSelect').val(),"29-20-2011","false");

                 fs_Mgs_Line_CpuUsage_Data("average",$('#fsSelect').val(),"29-20-2011","29-20-2011","false");
                 fs_Mgs_Line_MemoryUsage_Data("average",$('#fsSelect').val(),"29-20-2011","29-20-2011","false");
                 fs_Mgs_Line_DiskRead_Data("average","29-20-2011",$('#fsSelect').val(),"29-20-2011","false");
                 fs_Mgs_Line_DiskWrite_Data("average","29-20-2011",$('#fsSelect').val(),"29-20-2011","false");
			}
});         

/******************************************************************************/
// Function to populate breadcrumb on selecting particular oss/mgs/mds
/******************************************************************************/

		$("#ossSelect").live('change', function (){
			if($(this).val()!="")
			{
				$('#dashboardDiv').hide();$('#fileSystemDiv').hide();$('#ostInfoDiv').hide();
				$('#ossInfoDiv').slideDown("slow");
				 var breadCrumbHtml = "<ul>"+
				 "<li><a href='/dashboard'>Home</a></li>"+
				 "<li><a href='/dashboard'>All FileSystems</a></li>"+
				 "<li><a href='#' onclick='showFSDashboard()'>"+$('#fsSelect :selected').text()+"</a></li>"+
				 "<li>"+$('#ossSelect :selected').text()+"</li>"+
	             "<li>"+
	             "<select id='ostSelect'>"+
	             "<option value=''>Select OST</option>";
	             
				 $.post("/api/getvolumes/",{filesystem:$('#fsSelect').val()}) 
				    .success(function(data, textStatus, jqXHR) {
				    	if(data.success)
	                    {
	                        $.each(data.response, function(resKey, resValue)
	                        {
	                            if(resValue.kind=='OST')
	                            {
	                                 breadCrumbHtml  =  breadCrumbHtml + "<option value="+resValue.name+">"+resValue.name+"</option>";
	                            }
	                        });
	                    }
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
			//call for OSS graphs
			OSS_Pie_space_data($('#ossSelect').val());
			
			//call for inode select
			OSS_Pie_inode_data($('#ossSelect').val(),'29-20-2011','29-20-2011','average');
			
			//call for OSS CPU Usage
			OSS_Line_Cpu_data($('#ossSelect').val(),'29-20-2011','29-20-2011','average');
			
			//call for memory usage
			OSS_Line_Memory_Data($('#ossSelect').val(),'29-20-2011','29-20-2011','average');
	
			//call for disk read
			OSS_Line_DiskRead_Data($('#ossSelect').val(),'29-20-2011','29-20-2011','average');
			
			//call for disk write
			OSS_Line_DiskWrite_Data($('#ossSelect').val(),'29-20-2011','29-20-2011','average');
	    });
		
/******************************************************************************/
// Function to populate breadcrumb on selecting particular ost/mgt/mdt
/******************************************************************************/
		$("#ostSelect").live('change', function (){
			if($(this).val()!="")
			{
				$('#dashboardDiv').hide();$('#fileSystemDiv').hide();$('#ossInfoDiv').hide();
				$('#ostInfoDiv').slideDown("slow");
				 var breadCrumbHtml = "<ul>"+
				 "<li><a href='/dashboard'>Home</a></li>"+
				 "<li><a href='/dashboard'>All FileSystems</a></li>"+
				 "<li><a href='#' onclick='showFSDashboard()'>"+$('#fsSelect :selected').text()+"</a></li>"+
				 "<li><a href='#' onclick='showOSSDashboard()'>"+$('#ossSelect :selected').text()+"</a></li>"+
				 "<li>"+$('#ostSelect :selected').text()+"</li>"+
	    "</ul>";
	    
     $("#breadCrumb3").html(breadCrumbHtml);
			 	$("#breadCrumb3").jBreadCrumb();
				}
	//call for file system usage
	OST_Pie_Space_Data($("#ostSelect").val());
	
	//call for inode usage
	OST_Pie_Inode_Data($("#ostSelect").val(),'29-20-2011','29-20-2011','average');
	
	//call for disk read
	OST_Line_DiskRead_Data($("#ostSelect").val(),'29-20-2011','29-20-2011','average');
	
	//call for disk write
	OST_Line_DiskWrite_Data($("#ostSelect").val(),'29-20-2011','29-20-2011','average');
	 });
/******************************************************************************/
// Function for controlling tabs on oss dashboard
/******************************************************************************/				
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

/******************************************************************************/
// Function to show popup dialog on alert and event button click
/******************************************************************************/				

		$('#alerts_dialog').dialog({
			autoOpen: false,
			width: 800,
			height:400,
			show: "clip",
			modal: true,
			buttons: {
				"Ok": function() { 
					$(this).dialog("close"); 
				}
			}
		});

		$('#events_dialog').dialog({
			autoOpen: false,
			width: 800,
			height:400,
			show: "clip",
			modal: true,
			buttons: {
				"Ok": function() { 
					$(this).dialog("close"); 
				}
			}
		});
		
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

	db_Bar_Space_Data('false');
    db_Pie_Space_Data('false');
    db_Bar_INodes_Data('false');
    db_Pie_INodes_Data('false');
    db_Line_CpuUsage_Data('false');
    db_Line_MemoryUsage_Data('false');
    db_Line_DiskRead_Data('false');
    db_Line_DiskWrite_Data('false');
    db_Mgs_Line_CpuUsage_Data('false');
    db_Mgs_Line_MemoryUsage_Data('false');
    db_Mgs_Line_DiskRead_Data('false');
    db_Mgs_Line_DiskWrite_Data('false');
	
		$('#fs_space').click(function(){
			load_landingPageBar_disk('true');						
		});
		
		$('#db_cpu_usage').click(function(){
            db_Line_CpuUsage_Data('true');
		});
});			// End Of document.ready funtion
