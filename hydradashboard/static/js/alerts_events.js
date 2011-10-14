/*******************************************************************************************************************************************************
 * File name: alerts_events.js
 * 
 * Description: 
 * 1) Bind events for Alerts, Events and Jobs
 * 2) Contains seperate methods for loading only content for each type
 * 
 * // Functions:
 * 1) loadAlertContent
 * 2) loadEventContent
 * 3) loadJobContent
 * 
 *******************************************************************************************************************************************************/

$(document).ready(function() 
{
		$("#alertAnchor").click(function(){
			loadAlertContent('alert_content', 'active', 10);
		});  
		
		$("#eventsAnchor").click(function(){
			loadEventContent('event_content' , 10);	
		});  
		
		$("#jobsAnchor").click(function(){
			loadJobContent('job_content');
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


	    $("#minusImg").click(function()
	    {
	         $("#frmsignin").toggle("slow");
	         $("#signbtn").toggle("slow");
	         /*$(this).toggleClass("active");
	         $("#minusImg").hide();$("#plusImg").show();*/
	         return false;
	    });
});
//******************************************************************************/
// Function to load content for alerts
/******************************************************************************/
loadAlertContent = function(targetAlertDivName, status, maxCount)
{
	 	$('#'+targetAlertDivName).html('<tr><td width="100%" align="center"><img src="/static/images/loading.gif" style="margin-top:10px;margin-bottom:10px" width="16" height="16" /></td></tr>');
        var alertTabContent="";
        var isEmpty = "false";
        var cssClassName = "", imgName = "";
        var pagecnt=0
        var maxpagecnt=maxCount;
        $.post("/api/getalerts/",{"active": status})
        .success(function(data, textStatus, jqXHR) {
         if(data.success)
         {
             $.each(data.response, function(resKey, resValue)
             {
            	pagecnt++;
                if(maxpagecnt > pagecnt || maxpagecnt < 0)
                {
	            	cssClassName="",imgName="";
	                isEmpty = "true";
	                if(resValue.alert_severity == 'alert') //red
	                {
	                	cssClassName='palered';
	                	imgName="/static/images/dialog-error.png";
	                }
	                else if(resValue.alert_severity == 'info') //normal
	                {
	                	cssClassName='';
	            		imgName="/static/images/dialog-information.png";
	                }
	                else if(resValue.alert_severity == 'warning') //yellow
	                {
	                	cssClassName='brightyellow';
	                	imgName="/static/images/dialog-warning.png";
	                }
	                alertTabContent = alertTabContent + "<tr class='"+cssClassName+"'><td width='20%' align='left' valign='top' class='border' style='font-weight:normal'>" +  resValue.alert_created_at + "<td width='7%' align='left' valign='top' class='border'><img src='"+imgName+"' width='16' height='16' class='spacetop' /></td><td width='30%' align='left' valign='top' class='border' style='font-weight:normal'>" + resValue.alert_item +  "</td><td width='38%' align='left' valign='top' class='border' style='font-weight:normal'>" + resValue.alert_message + "</td></tr>";
                }
             });
         }
	    })
	    .error(function(event) {
	    	//	$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
	     })
	    .complete(function(event){
	         if(isEmpty == "false")
	         {
	        	 alertTabContent = alertTabContent + "<tr> <td colspan='5' align='center' class='alerts_all_ok'>No Active Alerts</td></tr>";
	         }
		     /*else
		     {
		    	 alertTabContent = alertTabContent + "<tr> <td colspan='5' align='right' bgcolor='#FFFFFF' style='font-family:Verdana, Arial, Helvetica, sans-serif;'><a href='/dashboard/dbalerts/'>(All Events)</a></td></tr>";
		     }*/
	         if(maxCount < 0 && isEmpty != "false")
				{
					$("#"+targetAlertDivName).html("<thead><tr><th>Alert Created At</th><th>Status</th><th>Host</th><th>Message</th></tr><thead><tbody>"+alertTabContent+"</tbody>");
					$("#"+targetAlertDivName).dataTable({
						 "aoColumns": [
			                { "sClass": 'txtleft' },
			                { "sClass": 'txtcenter' },
			                { "sClass": 'txtleft' },
			                { "sClass": 'txtleft' }
			              ]
					});
				}
				else
				{
					$("#"+targetAlertDivName).html(alertTabContent);
				} 
	         
	    });
}

//******************************************************************************/
//Function to load content for events 
/******************************************************************************/
loadEventContent = function(targetEventDivName, maxCount)
{
	 $('#'+targetEventDivName).html('<tr><td width="100%" align="center"><img src="/static/images/loading.gif" style="margin-top:10px;margin-bottom:10px" width="16" height="16" /></td></tr>');
	 var eventTabContent='';
	 var cssClassName = "", imgName = "";
     var pagecnt=0
     var maxpagecnt=maxCount;
     $.get("/api/getlatestevents/") 
    	.success(function(data, textStatus, jqXHR) {
    	 if(data.success)
         {
             $.each(data.response, function(resKey, resValue)
             {
                pagecnt++;
                if(maxpagecnt>pagecnt || maxpagecnt < 0)
                {
					if(resValue.event_severity == 'alert') //red
					{
						cssClassName='palered';
	                	imgName="/static/images/dialog-error.png";
					}
					else  if(resValue.event_severity == 'info') //normal
					{
						cssClassName='';
	            		imgName="/static/images/dialog-information.png";
					}
					else if(resValue.event_severity == 'warning') //yellow
					{
						cssClassName='brightyellow';
	                	imgName="/static/images/dialog-warning.png";
					}
					eventTabContent = eventTabContent + "<tr class='"+cssClassName+"'><td width='20%' align='left' valign='top' class='border' style='font-weight:normal'>" +  resValue.event_created_at + "</td><td width='7%' align='left' valign='top' class='border' class='txtcenter'><img src='"+imgName+"' width='16' height='16' class='spacetop'/></td><td width='30%' align='left' valign='top' class='border' style='font-weight:normal'>" + resValue.event_host +  "</td><td width='30%' align='left' valign='top' class='border' style='font-weight:normal'>" + resValue.event_message + "</td></tr>";
                }
             });
         }
    })
    .error(function(event) {
        //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
    })
    .complete(function(event){
			if(pagecnt == 0)
			{
				eventTabContent = eventTabContent + "<tr> <td colspan='5' align='center' bgcolor='#FFFFFF' style='font-family:Verdana, Arial, Helvetica, sans-serif;'><a href='#'>No Events</a></td></tr>";
			}
			/*else
			{
				eventTabContent = eventTabContent + "<tr><td colspan='5' align='right' bgcolor='#FFFFFF' style='font-family:Verdana, Arial, Helvetica, sans-serif;'><a href='/dashboard/dbevents/'>(All Events)</a></td></tr>";
			}*/
			if(maxCount < 0)
			{
				$("#"+targetEventDivName).html("<thead><tr><th>Event Created At</th><th>Status</th><th>Host</th><th>Message</th></tr><thead><tbody>"+eventTabContent+"</tbody>");
				$("#"+targetEventDivName).dataTable({
					 "aoColumns": [
		                { "sClass": 'txtleft' },
		                { "sClass": 'txtcenter' },
		                { "sClass": 'txtleft' },
		                { "sClass": 'txtleft' }
		              ]
				});
			}
			else
			{
				$("#"+targetEventDivName).html(eventTabContent);
			} 
    });
}

//******************************************************************************/
//Function to load content for jobs
/******************************************************************************/
loadLogContent = function(targetJobDivName, maxCount)
{
	    $('#'+targetJobDivName).html('<tr><td width="100%" align="center"><img src="/static/images/loading.gif" style="margin-top:10px;margin-bottom:10px" width="16" height="16" /></td></tr>');
		var jobTabContent;
		var isEmpty = "false";
		var maxpagecnt=maxCount;
		var pagecnt=0;
		$.post("/api/getlogs/",{"lustre": "", "day": 14, "month": 10}) 
		.success(function(data, textStatus, jqXHR) {
			 if(data.success)
		     {
		        $.each(data.response, function(resKey, resValue)
		        {
				   pagecnt++;
		           isEmpty = "true";
		           if (maxpagecnt > pagecnt || maxpagecnt < 0)
		           {
		        	   jobTabContent = jobTabContent + "<tr> <td>" + resValue.date + "<td>"+ resValue.host+"</td><td>"+ resValue.service +"</td><td>" + resValue.message + "</td></tr>";
		           }
		        });
		     }
		})
		.error(function(event) {
		   //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
		})
		.complete(function(event){
			if(isEmpty == "false")
			{
				jobTabContent = jobTabContent + "<tr> <td colspan='5' align='center' class='logs_all_ok'>No Logs</td></tr>";
			}
			/*else
			{
				jobTabContent = jobTabContent + "<tr><td colspan='5' align='right' bgcolor='#FFFFFF' style='font-family:Verdana, Arial, Helvetica, sans-serif;'><a href='/dashboard/dblogs/'>(All Jobs)</a></td></tr>";
			}*/
			if(maxCount < 0)
			{
				$("#"+targetJobDivName).html("<thead><tr><th>Log Created At</th><th>Host</th><th>Service</th><th>Message</th></tr><thead><tbody>"+jobTabContent+"</tbody>");
				$("#"+targetJobDivName).dataTable({
					 "aoColumns": [
		                { "sClass": 'txtleft' },
		                { "sClass": 'txtleft' },
		                { "sClass": 'txtleft' },
		                { "sClass": 'txtleft' }
		              ]
				});
			}
			else
			{
				$("#"+targetJobDivName).html(jobTabContent);
			} 
			
		});
}

loadHostList = function(fileSystemName)
{
	var hostList = '<option>All</option>';
	$.post("/api/listservers/",{filesystem:fileSystemName})
    .success(function(data, textStatus, jqXHR) {
         if(data.success)
         {
             $.each(data.response, function(resKey, resValue)
             {
                 if(resValue.kind=='OSS' || resValue.kind.indexOf('OSS')>0)
                 {
                	 hostList  =  hostList + "<option value="+resValue.host_address+">"+resValue.host_address+"</option>";
                 }
             });
         }
    })
    .error(function(event) {
        //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
    })
    .complete(function(event){
    	$('#db_events_hostList').html(hostList);
    });
}

loadJobContent = function(targetJobDivName)
{
	    $('#'+targetJobDivName).html('<tr><td width="100%" align="center"><img src="/static/images/loading.gif" style="margin-top:10px;margin-bottom:10px" width="16" height="16" /></td></tr>');
		var jobTabContent;
		var isEmpty = "false";
		var maxpagecnt=10;
		var pagecnt=0
		$.get("/api/getjobs/") 
		.success(function(data, textStatus, jqXHR) {
			 if(data.success)
		     {
		        $.each(data.response, function(resKey, resValue)
		        {
				   pagecnt++;
		           isEmpty = "true";
		           if (maxpagecnt > pagecnt)
		           {
		        	   jobTabContent = jobTabContent + "<tr> <td width='35%' align='left' valign='top' class='border' style='font-weight:normal'>" + resValue.description + "<td width='15%' align='left' valign='top' class='border'><input name='Details' type='button' value='Cancel' /></td><td width='18%' align='center' valign='top' class='border' style='font-weight:normal'><a href='#'>Details</a></td><td width='30%' align='left' valign='top' class='border' style='font-weight:normal'>" + resValue.created_at + "</td></tr>";
		           }
		        });
		     }
		})
		.error(function(event) {
		   //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
		})
		.complete(function(event){
			if(isEmpty == "false")
			{
				jobTabContent = jobTabContent + "<tr> <td colspan='5' align='center' bgcolor='#FFFFFF' style='font-family:Verdana, Arial, Helvetica, sans-serif;'><a href='#'>No Jobs</a></td></tr>";
			}
			else
			{
				jobTabContent = jobTabContent + "<tr><td colspan='5' align='right' bgcolor='#FFFFFF' style='font-family:Verdana, Arial, Helvetica, sans-serif;'><a href='/dashboard/dblogs/'>(All Jobs)</a></td></tr>";
			}
			$("#"+targetJobDivName).html(jobTabContent);
		});
}

