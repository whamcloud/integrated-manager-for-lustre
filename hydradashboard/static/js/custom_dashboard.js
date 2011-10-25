/*****************************************************************************/
// Page Ready :: Load breadcrumbs for navigation
//            :: Bind events for breadcrumbs navigation  
//            :: Bind events for Jobs, Alerts and Events 
/*****************************************************************************/
$(document).ready(
function() 
{

/********************************************************************************
// Function to populate landing page 
/********************************************************************************/
	loadView = function(key){
		switch (key) 
		{
			case "#fs":
					window.location.hash =  "fs";
					loadFSContent($('#ls_filesystem').val());
					break;
			case "#oss":
					window.location.hash =  "oss";
					loadOSSContent($('#ls_filesystem').val(), $('#ls_oss').val());
					break;
			case "#ost":
					window.location.hash =  "ost";
					loadOSTContnent($('#ls_filesystem').val(), $('#ls_oss').val(), $('#ls_ost').val());
					break;
			
			default:
					loadLandingPage();
		}
	};
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
  $("#plusImg").click(function(){
        $(".panel").toggle("slow");
        $("#plusImg").hide();$("#minusImg").show();
        $(this).toggleClass("active");
        return false;
  });
		
/******************************************************************************/
// Function for showing time interval units
/******************************************************************************/
		
		$("select[id=intervalSelect]").change(function(){
			var intervalValue = $(this).val();
			var unitSelectOptions = "";
			if(intervalValue == "")
			{
				unitSelectOptions = "<option value=''>Select</option>";
			}
			else if(intervalValue == "minutes")
			{
				unitSelectOptions = getUnitSelectOptions(61);
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
			$("select[id=unitSelect]").html(unitSelectOptions);
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
		
		function resetTimeInterval()
		{
			$("select[id=intervalSelect]").attr("value","");
			$("select[id=unitSelect]").html("<option value=''>Select</option>");
			$("select[id=unitSelect]").attr("value","");
		}
		
		$("select[id=unitSelect]").change(function(){
			setStartEndTime($(this).prev('select').find('option:selected').val(), $(this).find('option:selected').val(), "");
		});
		
		setStartEndTime = function(timeFactor, startTimeValue, endTimeValue)
		{
			endTime = endTimeValue;
			
			if(timeFactor == "minutes")
				startTime = startTimeValue;
			else if(timeFactor == "hour")
				startTime = startTimeValue * 60;
				
			if(! $('#dashboardDiv').is(':hidden'))
				initDashboardPolling();
			else if(! $('#fileSystemDiv').is(':hidden'))
				initFileSystemPolling();
			else if(! $('#ossInfoDiv').is(':hidden'))
				initOSSPolling();
			else if(! $('#ostInfoDiv').is(':hidden'))
				initOSTPolling();
		}
		
/******************************************************************************/
// Function to load landing page
/******************************************************************************/
		loadLandingPage = function(){     	
			var allfileSystemsSummaryContent = "<tr><td align='center' colspan='4'><b>All Filesystems Summary</b></td></tr>"+
         	"<tr><td width='25%' align='left' valign='top' ><span class='fontStyle style2 style9'><b>File system</b></span><td width='5%' align='right' valign='top' ><span class='fontStyle style2 style9'><b>OSS</b></span></td><td width='5%' align='right' valign='top' ><span class='fontStyle style2 style9'><b>OST</b></span></td><td width='33%' align='right' valign='top' ><span class='fontStyle style2 style9'><b>Total Space</b></span></td><td width='33%' align='right' valign='top' ><span class='fontStyle style2 style9'><b>Free Space</b></span></td></tr>";
         	$.get("/api/listfilesystems")
			        .success(function(data, textStatus, jqXHR) {		//<option value='sobofs01'>sobofs01</option>
			            var innerContent = "<option value=''>Select File System</option>";
			            $.each(data, function(key, val) {
			                if(key=='success' && val == true)
			                {
			                    $.each(data, function(key1, val1) {
			                    if(key1=='response')
			                    {
			                        $.each(val1, function(resKey, resValue) {
			                            innerContent = innerContent + "<option value="+resValue.fsname+">"+resValue.fsname+"</option>";
			                            allfileSystemsSummaryContent = allfileSystemsSummaryContent +
			                            "<tr><td width='25%' align='left' valign='top' ><span class='fontStyle style2 style9'>"+resValue.fsname+"</span><td width='5%' align='right' valign='top' ><span class='fontStyle style2 style9'></span>"+resValue.noofoss+"</td><td width='5%' align='right' valign='top' ><span class='fontStyle style2 style9'>"+resValue.noofost+"</span></td><td width='33%' align='right' valign='top' ><span class='fontStyle style2 style9'>"+resValue.kbytesused+"</span></td><td width='33%' align='right' valign='top' ><span class='fontStyle style2 style9'>"+resValue.kbytesfree+"</span></td></tr>";
			                            
			                            $('#allFileSystemSummaryTbl').dataTable({
			                                "aoColumns": [
				   		                                   { "sClass": 'txtleft', "sWidth": "25%" },
				   		                                   { "sClass": 'txtright',"sWidth": "5%" },
				   		                                   { "sClass": 'txtright',"sWidth": "5%" },
				   		                                   { "sClass": 'txtright',"sWidth": "33%" },
				   		                                   { "sClass": 'txtright',"sWidth": "33%" }
				   		                                 ],
				   		                                "iDisplayLength":5,
				   		                                "bRetrieve":true,
				   		                             	"bFilter":false,
				   		                             	"bLengthChange": false,
				   		                             
				   		                    }).fnAddData ([
	                                           resValue.fsname,
	                                           resValue.noofoss,
	                                           resValue.noofost,
	                                           resValue.kbytesused,
	                                           resValue.kbytesfree,
	                                        ]);
			                        });
			                    }
			                    });
			                }
			            });
			            $('#fsSelect').html(innerContent);
			           // $('#allFileSystemSummaryTbl').html(allfileSystemsSummaryContent);
			            
			        })
					.error(function(event) {
					});
    }   

/******************************************************************************/
// Function to populate oss/mds/mgs list on selecting particular file system
/******************************************************************************/
		
$("#fsSelect").change(function(){
			if($(this).val()!="")
			{
				loadFSContent($(this).val());
			}
});         

loadFSContent = function(fsName)
{

	 $('#dashboardDiv').hide();$('#ossInfoDiv').hide();$('#ostInfoDiv').hide();
	 $('#fileSystemDiv').slideDown("slow");
	 var breadCrumbHtml = "<ul>"+
	 "<li><a href='/dashboard'>Home</a></li>"+
	 "<li><a href='/dashboard'>All FileSystems</a></li>"+
	 "<li>"+fsName+"</li>"+
	 "<li>"+
    "<select id='ossSelect'>"+
    "<option value=''>Select OSS</option>";

    $.post("/api/listservers/",{filesystem:fsName}) 
   .success(function(data, textStatus, jqXHR) {
   	 if(data.success)
        {
            $.each(data.response, function(resKey, resValue)
            {
                if(resValue.kind.indexOf('OST')!=-1)
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

		    // 2011-10-17 19:56:58.720036  2011-10-17 19:46:58.720062
   fs_Bar_SpaceUsage_Data(fsName, startTime, endTime, "Average", "OST", spaceUsageFetchMatric, false);

   fs_Line_connectedClients_Data(fsName, startTime, endTime, "Average", clientsConnectedFetchMatric, false);

   fs_LineBar_CpuMemoryUsage_Data(fsName, startTime, endTime, "Average", "OST", cpuMemoryFetchMatric, false);

   fs_Area_ReadWrite_Data(fsName, startTime, endTime, "Average", "MDT", readWriteFetchMatric, false);

   fs_Area_Iops_Data(fsName, startTime, endTime, "Average", "MDT", iopsFetchmatric, false);

   //fs_HeatMap_Data('false');

   clearInterval(dashboardPollingInterval);

   loadFileSystemSummary(fsName);
   
   $('#ls_filesystem').attr("value",fsName);
   window.location.hash =  "fs";
   
   resetTimeInterval();

}

/******************************************************************************/
// Function to populate breadcrumb on selecting particular oss/mgs/mds
/******************************************************************************/

		$("#ossSelect").live('change', function (){
			if($(this).val()!="")
			{
				loadOSSContent($('#ls_filesystem').val(), $(this).val());
			}	
		});
		
		loadOSSContent = function(fsName, ossName){
			$('#dashboardDiv').hide();$('#fileSystemDiv').hide();$('#ostInfoDiv').hide();
			$('#ossInfoDiv').slideDown("slow");
			 var breadCrumbHtml = "<ul>"+
			 "<li><a href='/dashboard'>Home</a></li>"+
			 "<li><a href='/dashboard'>All FileSystems</a></li>"+
			 "<li><a href='#' onclick='showFSDashboard()'>"+fsName+"</a></li>"+
			 "<li>"+ossName+"</li>"+
             "<li>"+
             "<select id='ostSelect'>"+
             "<option value=''>Select OST</option>";
             
			 $.post("/api/getvolumes/",{filesystem:fsName}) 
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
	        
	
	        oss_LineBar_CpuMemoryUsage_Data(fsName, startTime, endTime, "Average", cpuMemoryFetchMatric, 'false');
	
	        oss_Area_ReadWrite_Data(fsName, startTime, endTime, "Average", "OST", readWriteFetchMatric, 'false');
	
	        loadOSSUsageSummary(fsName);
	        
	        $('#ls_oss').attr("value",ossName);
	        window.location.hash =  "oss";
	        
	        resetTimeInterval();
	}
			
/******************************************************************************/
// Function to populate breadcrumb on selecting particular ost/mgt/mdt
/******************************************************************************/
		$("#ostSelect").live('change', function (){
			if($(this).val()!="")
			{
				loadOSTContnent($('#ls_filesystem').val(), $('#ls_oss').val(), $(this).val());
			}	
	
     });
	loadOSTContnent = function(fsName, ossName, ostName){
		$('#dashboardDiv').hide();$('#fileSystemDiv').hide();$('#ossInfoDiv').hide();
		$('#ostInfoDiv').slideDown("slow");
		 var breadCrumbHtml = "<ul>"+
		 "<li><a href='/dashboard'>Home</a></li>"+
		 "<li><a href='/dashboard'>All FileSystems</a></li>"+
		 "<li><a href='#' onclick='showFSDashboard()'>"+fsName+"</a></li>"+
		 "<li><a href='#' onclick='showOSSDashboard()'>"+ossName+"</a></li>"+
		 "<li>"+ostName+"</li>"+
		 "</ul>";

		 $("#breadCrumb3").html(breadCrumbHtml);
	 	 $("#breadCrumb3").jBreadCrumb();
	
		/* HYD-375: ostSelect value is a name instead of an ID */
		load_resource_graph("ost_resource_graph_canvas", ostName);
		
		ost_Pie_Space_Data(ostName, "", "", 'Average', 'OST', spaceUsageFetchMatric, 'false');
		ost_Pie_Inode_Data(ostName, "", "", 'Average', 'OST', spaceUsageFetchMatric, 'false');
		ost_Area_ReadWrite_Data(ostName, startTime, endTime, 'Average', 'OST', readWriteFetchMatric, false);
		
		loadOSTSummary(fsName);
		
		$('#ls_ost').attr("value",ostName);
		window.location.hash =  "ost";
	}
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

		db_Bar_SpaceUsage_Data('false');
        db_Line_connectedClients_Data('false');
        db_LineBar_CpuMemoryUsage_Data('false');
        db_Area_ReadWrite_Data('false');
        db_Area_Iops_Data('false');
        //db_HeatMap_Data('false');

});			// End Of document.ready funtion


