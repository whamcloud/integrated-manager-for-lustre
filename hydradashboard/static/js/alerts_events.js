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
var ERROR_PNG = "/static/images/dialog-error.png";
var CORRECT_GIF = "/static/images/dialog_correct.png";
var WARNING_PNG = "/static/images/dialog-warning.png";
var INFO_PNG = "/static/images/dialog-information.png";
var PAUSE_PNG = "/static/images/gtk-media-pause.png";
var CANCEL_PNG = "/static/images/gtk-cancel.png";
var RUNNING_GIF = "/static/images/loading.gif";

var job_action_buttons = ['Pause', 'Resume', 'Cancel', 'Complete'];

$(document).ready(function() 
{
  $("#alertAnchor").click(function()
  {
    toggleSliderDiv('alertsDiv');
    if($('#alertsDiv').css('display') == 'block')
    {
      loadAlertContent('alert_content', 10);  // load only when target div visible
    }
  });
  
  $("#eventsAnchor").click(function()
  {
    toggleSliderDiv('eventsDiv')
    if($('#eventsDiv').css('display') == 'block')
    {
      loadEventContent('event_content' , 10);
    }
  });
  
  $("#jobsAnchor").click(function()
  {
    toggleSliderDiv('jobsDiv');
    if($('#jobsDiv').css('display') == 'block')
    {
      loadJobContent('job_content');
    }
  });
  
  $("#minusImg").click(function()
  {
   $("#frmsignin").toggle("slow");
   $("#signbtn").toggle("slow");
   return false;
  });
});

getCssClass = function(severity_value)
{
  var cssClassName = "";
  if(severity_value == 'alert') //red
    cssClassName='palered';
  else if(severity_value == 'info') //normal
    cssClassName='';
  else if(severity_value == 'warning') //yellow
    cssClassName='brightyellow';
  
  return cssClassName;
}

getImage = function(severity_value)
{
  var imgName="";
  if(severity_value == 'alert') //red
    imgName = ERROR_PNG;
  else if(severity_value == 'info') //normal
    imgName = INFO_PNG;
  else if(severity_value == 'warning') //yellow
    imgName = WARNING_PNG;
  
  return imgName;
}

toggleSliderDiv = function(divname)
{
  var slider_divs =['alertsDiv','eventsDiv','jobsDiv'];
  for (var i = 0 ;i < slider_divs.length ; i++)
  { 
    if (slider_divs[i] == divname)
    {
      if($("#"+divname).css("display") == "none")
      {
        $("#"+divname).css("display","block");
      }
      else
      {
        $("#"+divname).css("display","none");
      }    
    }
    else
    {
      $("#"+slider_divs[i]).hide();
    }
  }
}

progress_show = function(divname)
{
  $('#'+ divname).html('<tr>' +
                       '<td width="100%" align="center">' +
                       '<img src="/static/images/loading.gif" style="margin-top:10px;margin-bottom:10px" width="16" height="16" />' +
                       '</td></tr>');
}

//******************************************************************************/
// Function to load content for alerts
/******************************************************************************/
loadAlertContent = function(targetAlertDivName, maxCount)
{
  var alertTabContent="";
  var pagecnt=0
  var maxpagecnt=maxCount;
  progress_show(targetAlertDivName);

  invoke_api_call(api_get, "alert/", {active: true, iDisplayStart: 0, iDisplayCount: maxCount}, 
  success_callback = function(data)
  {
    $.each(data.aaData, function(resKey, resValue)
    {
      pagecnt++;
      if(maxpagecnt > pagecnt || maxpagecnt < 0)
      {
        var imgName = getImage(resValue.alert_severity);

        alertTabContent = alertTabContent + 
                          "<tr>" +
                          "<td width='20%' align='left' class='border' valign='top'>" +  
                            resValue.alert_created_at + 
                          "</td>" +
                          "<td width='7%' align='left' class='border' valign='top'>" +
                          "<img src='" + imgName + "' width='16' height='16' class='spacetop' />" +
                          "</td>" +
                          "<td width='30%' align='left' class='border' valign='top'>" + 
                            resValue.alert_item +  
                          "</td>" + 
                          "<td width='38%' align='left' class='border' valign='top'>" + 
                            resValue.alert_message + 
                          "</td>" + 
                          "</tr>";
      }
    });

    if(pagecnt == 0)
    {
      alertTabContent = alertTabContent + "<tr> <td colspan='5' align='center' class='no_notification'>No Alerts</td></tr>";
    }
    $("#"+targetAlertDivName).html(alertTabContent);
  });
}

loadEventContent = function(targetEventDivName, maxCount)
{
  var eventTabContent='';
  var pagecnt=0
  var maxpagecnt=maxCount;
  progress_show(targetEventDivName);
  
  invoke_api_call(api_get, "event/", {iDisplayStart: 0, iDisplayLength: 10},
    success_callback = function(data)
    {
      var events = data['aaData'];
      $.each(events, function(i, event_record)
      {
        pagecnt++;
        if(maxpagecnt > pagecnt || maxpagecnt < 0)
        {
          var cssClassName = getCssClass(event_record.severity);
          var imgName = getImage(event_record.severity);
          
          eventTabContent = eventTabContent +
                            "<tr class='" + cssClassName + "'>" +
          		              "<td width='20%' align='left' valign='top' class='border' style='font-weight:normal'>" +  
          		              event_record.created_at + 
          		              "</td>" +
          		              "<td width='7%' align='left' valign='top' class='border' class='txtcenter'>" +
          		              "<img src='" + imgName + "' width='16' height='16' class='spacetop'/>" +
          		              "</td>" +
          		              "<td width='30%' align='left' valign='top' class='border' style='font-weight:normal'>" + 
          		              event_record.host_name +  "&nbsp;" +
          		              "</td>" +
          		              "<td width='30%' align='left' valign='top' class='border' style='font-weight:normal'>" + 
          		              event_record.message + 
          		              "</td>" +
          		              "</tr>";
        }
      });

      if(pagecnt == 0)
      {
        eventTabContent = eventTabContent + "<tr> <td colspan='5' align='center' class='no_notification'>No Events</td></tr>";
      }
      $("#"+targetEventDivName).html(eventTabContent);
    });
}

loadJobContent = function(targetJobDivName)
{
  var jobTabContent="";
  var maxpagecnt=10;
  var pagecnt=0;
  progress_show(targetJobDivName);
  
  invoke_api_call(api_get, "getjobs", "",
    success_callback = function(data)
    {
      $.each(data, function(resKey, resValue)
      {
        pagecnt++;
        var image_path = "";
        
        if(resValue.state == job_action_buttons[0].toLowerCase())
          image_path = PAUSE_PNG;
        else if(resValue.state == job_action_buttons[2].toLowerCase() || resValue.cancelled)
          image_path = CANCEL_PNG;
        else if(resValue.errored)
          image_path = ERROR_PNG;
        else if(resValue.state == job_action_buttons[3].toLowerCase())
          image_path = CORRECT_GIF;
        else if(resValue.state != job_action_buttons[3].toLowerCase() && resValue.state != job_action_buttons[0].toLowerCase())
          image_path = RUNNING_GIF;
                
        jobTabContent = jobTabContent +
                        "<tr>" +
                        "<td width='35%' align='left' valign='top' class='border' style='font-weight:normal'>" +
                        "<img src="+image_path+ " />" +
                        resValue.description + 
                        "</td>" + 
                        "<td width='40%' align='left' valign='top' class='border'>&nbsp;";

                        if(resValue.state != job_action_buttons[3].toLowerCase()
                            && resValue.state != job_action_buttons[0].toLowerCase())       // for adding pause button
                        {
                          jobTabContent = jobTabContent + "&nbsp;" + createButtonForJob(resValue.id, job_action_buttons[0]);
                        }
                        
                        if(resValue.state == job_action_buttons[0].toLowerCase())           // for adding resume button
                        {
                          jobTabContent = jobTabContent + "&nbsp;" + createButtonForJob(resValue.id, job_action_buttons[1]);
                        }
                        
                        if(resValue.state != job_action_buttons[3].toLowerCase())           // for adding cancel button
                        {
                          jobTabContent = jobTabContent + "&nbsp;" + createButtonForJob(resValue.id, job_action_buttons[2]);
                        }

                        jobTabContent = jobTabContent +
                        "</td>" +
                        "<td width='25%' align='left' valign='top' class='border' style='font-weight:normal'>" + 
                        resValue.created_at +
                        "</td>" +
                        "</tr>";
      });

      if(pagecnt == 0)
      {
        jobTabContent = jobTabContent + "<tr> <td colspan='5' align='center' class='no_notification'>No Jobs</td></tr>";
      }
      $("#"+targetJobDivName).html(jobTabContent);
    });
}

createButtonForJob = function(job_id, status)
{
  var button = "<input type='button' class='ui-button ui-state-default ui-corner-all ui-button-text-only notification_job_buttons' " +
              "onclick=job_action("+job_id+",'"+status.toLowerCase()+"') value="+status+" />";
  return button;
}

job_action = function(job_id, state)
{
  var api_params = {
      "job_id": job_id,
      "state": state
  };

  invoke_api_call(api_post, "set_job_status/", api_params,
  success_callback = function(data)
  {
    loadJobContent('job_content');
  });
}

loadHostList = function(filesystem_id, targetContainer)
{
  var hostList = '<option value="">All</option>';
  
  var api_params = {'filesystem_id':filesystem_id};

  invoke_api_call(api_get, "host/", api_params,
  success_callback = function(data)
  {
    $.each(data, function(resKey, resValue)
    {
      hostList  =  hostList + "<option value="+resValue.id+">"+resValue.pretty_name+"</option>";
    });
    $('#'+targetContainer).html(hostList);
  });
}

setActiveMenu = function(menu_element){
  $('#'+menu_element).addClass('active');
}
