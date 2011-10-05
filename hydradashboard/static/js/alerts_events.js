/*****************************************************************************/
// Page Ready :: Load breadcrumbs for navigation
//            :: Bind events for breadcrumbs navigation  
//            :: Bind events for Jobs, Alerts and Events 
/*****************************************************************************/
$(document).ready(
function() 
{
//******************************************************************************/
// Function to populate alerts
/******************************************************************************/
		$("#plusImg").click(function(){
				 var alertTab;
			     $.post("/api/getalerts/",{"active": ""}) 
			    	.success(function(data, textStatus, jqXHR) {
			    	 if(data.success)
	                 {
	                     $.each(data.response, function(resKey, resValue)
	                     {
							if(resValue.alert_severity == 'alert') //red
							{
							alertTab = alertTab + "<tr class='palered'><td width='20%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" +  resValue.alert_created_at + "</span><td width='7%' align='left' valign='top' class='border'><span class='style10'><img src='../static/images/dialog-error.png' width='16' height='16' class='spacetop' /></span></td><td width='30%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.alert_item +  "</span></td><td width='38%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.alert_message + "</td></tr>";
							}
							else if(resValue.alert_severity == 'info') //normal
							{
								alertTab = alertTab + "<tr><td width='20%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" +  resValue.alert_created_at + "</span><td width='7%' align='left' valign='top' class='border'><span class='style10'><img src='../static/images/dialog-information.png' width='16' height='16' class='spacetop' /></span></td><td width='30%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.alert_item +  "</span></td><td width='38%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.alert_message + "</td></tr>";
							}
							else if(resValue.alert_severity == 'warning') //yellow
							{
								alertTab = alertTab + "<tr class='brightyellow'><td width='20%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" +  resValue.alert_created_at + "</span><td width='7%' align='left' valign='top' class='border'><span class='style10'><img src='../static/images/dialog-warning.png' width='16' height='16' class='spacetop' /></span></td><td width='30%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.alert_item +  "</span></td><td width='38%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.alert_message + "</td></tr>";resValue.alert_item +  "</span></td><td width='38%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.alert_message + "</td></tr>";
							}
	                     });
	                 }
			    })
			    .error(function(event) {
			        //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
			    })
			    .complete(function(event){
								   alertTab = alertTab + "<tr> <td colspan='5' align='right' bgcolor='#FFFFFF' style='font-family:Verdana, Arial, Helvetica, sans-serif;'><a href='#'>(All Events)</a></td></tr>"
		             $("#alert_content").html(alertTab);
			    });
	});  
		
		
//******************************************************************************/
// Function for events
/******************************************************************************/
$("#eventsAnchor").click(function(){
				 var eventTab;
			     $.get("/api/getlatestevents/") 
			    	.success(function(data, textStatus, jqXHR) {
			    	 if(data.success)
	                 {
	                     $.each(data.response, function(resKey, resValue)
	                     {
							if(resValue.event_severity == 'alert') //red
							{
							eventTab = eventTab + "<tr class='palered'><td width='20%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" +  resValue.event_created_at + "</span></td><td width='7%' align='left' valign='top' class='border'><span class='style10'><img src='../static/images/dialog-error.png' width='16' height='16' class='spacetop'/></span></td><td width='30%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.event_host +  "</span></td><td width='38%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.event_message + "</span></td></tr>";
							}
							else  if(resValue.event_severity == 'info') //normal
							{
								eventTab = eventTab + "<tr><td width='20%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" +  resValue.event_created_at + "</span></td><td width='7%' align='left' valign='top' class='border'><span class='style10'><img src='../static/images/dialog-information.png' width='16' height='16' class='spacetop'/></span></td><td width='30%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.event_host +  "</span></td><td width='30%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.event_message + "</span></td></tr>";
							}
							else if(resValue.event_severity == 'warning') //yellow
							{
								eventTab = eventTab + "<tr class='brightyellow'><td width='20%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" +  resValue.event_created_at + "</span></td><td width='7%' align='left' valign='top' class='border'><span class='style10'><img src='../static/images/dialog-warning.png' width='16' height='16' class='spacetop'/></span></td><td width='30%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.event_host +  "</span></td><td width='30%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.event_message + "</span></td></tr>";
							}
	                     });
	                 }
			    })
			    .error(function(event) {
			        //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
			    })
			    .complete(function(event){
					eventTab = eventTab + "<tr><td colspan='5' align='right' bgcolor='#FFFFFF' style='font-family:Verdana, Arial, Helvetica, sans-serif;'><a href='#'>(All Events)</a></td></tr>";
		             $("#event_content").html(eventTab);
			    });
	});  



//******************************************************************************/
// Function for jobs
/******************************************************************************/
$("#jobsAnchor").click(function(){
				 var jobTab;
			     $.get("/api/getjobs/") 
			    	.success(function(data, textStatus, jqXHR) {
			    	 if(data.success)
	                 {
	                     $.each(data.response, function(resKey, resValue)
	                     {
							jobTab = jobTab + "<tr> <td width='35%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.description + "</span><td width='15%' align='left' valign='top' class='border'><input name='Details' type='button' value='Cancel' /></td><td width='18%' align='center' valign='top' class='border'><span class='fontStyle style2 style9'><a href='#'>Details</a></span></td><td width='30%' align='left' valign='top' class='border'><span class='fontStyle style2 style9'>" + resValue.created_at + "</span></td></tr>";
	                     });
	                 }
			    })
			    .error(function(event) {
			        //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
			    })
			    .complete(function(event){
					jobTab = jobTab + "<tr><td colspan='5' align='right' bgcolor='#FFFFFF' style='font-family:Verdana, Arial, Helvetica, sans-serif;'><a href='#'>(All Jobs)</a></td></tr>";
		             $("#job_content").html(jobTab);
			    });
	}); 
		
		});			// End Of document.ready funtion