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
var CORRECT_GIF = "/static/images/dialog_correct.gif";
var WARNING_PNG = "/static/images/dialog-warning.png";
var INFO_PNG = "/static/images/dialog-information.png";

$(document).ready(function() 
{
  $("#alertAnchor").click(function()
  {
    toggleSliderDiv('alertsDiv')
    loadAlertContent('alert_content', 'True', 10);
  });
  
  $("#eventsAnchor").click(function()
  {
    toggleSliderDiv('eventsDiv')
    loadEventContent('event_content' , 10);
  });
  
  $("#jobsAnchor").click(function()
  {
    toggleSliderDiv('jobsDiv');      
    loadJobContent('job_content');
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
loadAlertContent = function(targetAlertDivName, status, maxCount)
{
  var alertTabContent="";
  var pagecnt=0
  var maxpagecnt=maxCount;
  progress_show(targetAlertDivName);

  $.post("/api/getalerts/",{"active": status,"page_id":"","page_size":""})
  .success(function(data, textStatus, jqXHR) 
  {
    if(data.success)
    {
      $.each(data.response.aaData, function(resKey, resValue)
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
    }
  })
  .error(function(event) {})
  .complete(function(event)
  {
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
  $.get("/api/getlatestevents/") 
  .success(function(data, textStatus, jqXHR) 
  {
    if(data.success)
    {
      $.each(data.response, function(resKey, resValue)
      {
        pagecnt++;
        if(maxpagecnt > pagecnt || maxpagecnt < 0)
        {
          var cssClassName = getCssClass(resValue.event_severity);
          var imgName = getImage(resValue.event_severity);
          
          eventTabContent = eventTabContent +
                            "<tr class='" + cssClassName + "'>" +
          		              "<td width='20%' align='left' valign='top' class='border' style='font-weight:normal'>" +  
          		              resValue.date + 
          		              "</td>" +
          		              "<td width='7%' align='left' valign='top' class='border' class='txtcenter'>" +
          		              "<img src='" + imgName + "' width='16' height='16' class='spacetop'/>" +
          		              "</td>" +
          		              "<td width='30%' align='left' valign='top' class='border' style='font-weight:normal'>" + 
          		              resValue.event_host +  "&nbsp;" +
          		              "</td>" +
          		              "<td width='30%' align='left' valign='top' class='border' style='font-weight:normal'>" + 
          		              resValue.event_message + 
          		              "</td>" +
          		              "</tr>";
        }
      });
    }
  })
  .error(function(event) { })
  .complete(function(event)
  {
    if(pagecnt == 0)
    {
      eventTabContent = eventTabContent + "<tr> <td colspan='5' align='center' class='no_notification'>No Events</td></tr>";
    }
    $("#"+targetEventDivName).html(eventTabContent);
  });
}

loadJobContent = function(targetJobDivName)
{
  var jobTabContent;
  var maxpagecnt=10;
  var pagecnt=0;
  progress_show(targetJobDivName);
  $.get("/api/getjobs/")
  .success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      $.each(data.response, function(resKey, resValue)
      {
        pagecnt++;
        if (maxpagecnt > pagecnt)
        {
          jobTabContent = jobTabContent + 
                          "<tr>" +
                          "<td width='35%' align='left' valign='top' class='border' style='font-weight:normal'>" +
                          resValue.description + 
                          "</td>" + 
                          "<td width='15%' align='left' valign='top' class='border'>" +
                          "&nbsp;" +
                          "</td>" +
                          "<td width='18%' align='center' valign='top' class='border' style='font-weight:normal'>" +
                          "&nbsp;" +
                          "</td>" +
                          "<td width='30%' align='left' valign='top' class='border' style='font-weight:normal'>" + 
                          resValue.created_at + 
                          "</td>" +
                          "</tr>";
        }
      });
    }
  })
  .error(function(event) { })
  .complete(function(event)
  {
    if(pagecnt == 0)
    {
      jobTabContent = jobTabContent + "<tr> <td colspan='5' align='center' class='no_notification'>No Jobs</td></tr>";
    }
    $("#"+targetJobDivName).html(jobTabContent);
  });
}

loadHostList = function(filesystem_id, targetContainer)
{
  var hostList = '<option value="">All</option>';
  $.post("/api/listservers/",{'filesystem_id':filesystem_id})
  .success(function(data, textStatus, jqXHR) 
  {
    if(data.success)
    {
      $.each(data.response, function(resKey, resValue)
      {
        hostList  =  hostList + "<option value="+resValue.id+">"+resValue.pretty_name+"</option>";
      });
    }
  })
  .error(function(event) {
  })
  .complete(function(event){
  $('#'+targetContainer).html(hostList);
  });
}
 
setActiveMenu = function(menu_element){
    $('#'+menu_element).addClass('active');
}
