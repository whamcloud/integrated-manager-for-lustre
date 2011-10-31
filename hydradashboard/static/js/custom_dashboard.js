/*******************************************************************************
 * File name: custom_dasboard.js
 * Description: Common functions required by dashboard
 * ------------------ Data Loader functions--------------------------------------
 * 1) loadView(key)
 * 2) load_breadcrumbs
 * 3) $("#plusImg").click();
 * 4) $("select[id=intervalSelect]").change();
 * 5) getUnitSelectOptions(countNumber)
 * 6) resetTimeInterval
 * 7) $("select[id=unitSelect]").change();
 * 8) setStartEndTime(timeFactor, startTimeValue, endTimeValue)
 * 9) loadLandingPage
 * 10) $("#fsSelect").change();
 * 11) loadFSContent(fsName)
 * 12) $("#ossSelect").live('change');
 * 13) loadOSSContent(fsName, ossName);
 * 14) $("#ostSelect").live('change');
 * 15) loadOSTContnent(fsName, ossName, ostName);
 * 16) $("ul.tabs li").click();
 * 17) $("#heatmap_parameter_select").change();
 * 18) reloadHeatMap(fetchmetric);
/*****************************************************************************/
$(document).ready(function()
{
/********************************************************************************
// Function to populate landing page 
/********************************************************************************/
 loadView = function(key)
 {
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
/******************************************************************************
 * Function to load breadcrumb
******************************************************************************/
  load_breadcrumbs = function()
  {		
    $("#breadCrumb0").jBreadCrumb();
  }
/******************************************************************************
 * Events for controlling left panel
/******************************************************************************/
  $("#plusImg").click(function()
  {
    $(".panel").toggle("slow");
    $("#plusImg").hide();$("#minusImg").show();
    $(this).toggleClass("active");
    return false;
  });
/******************************************************************************
 * Function for showing time interval units
******************************************************************************/
  $("select[id=intervalSelect]").change(function()
  {
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
/*******************************************************************************
 * Function to reset options of the time interval and units selectbox
********************************************************************************/
  function resetTimeInterval()
  {
    $("select[id=intervalSelect]").attr("value","");
    $("select[id=unitSelect]").html("<option value=''>Select</option>");
    $("select[id=unitSelect]").attr("value","");
    startTime = "5";
    endTime = "";
  }
/*******************************************************************************
 * Function to show unit options on selection of time interval
********************************************************************************/
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
/******************************************************************************
 * Function to load landing page
******************************************************************************/
  loadLandingPage = function()
  {     	
    var allfileSystemsSummaryContent = "<tr>"+
    "<td align='center' colspan='4'>"+
    "<b>All Filesystems Summary</b></td>" +
    "</tr>"+
    "<tr>"+
    "<td width='25%' align='left' valign='top'>"+
    "<span class='fontStyle style2 style9'><b>File system</b></span></td>"+
    "<td width='5%' align='right' valign='top'>"+
    "<span class='fontStyle style2 style9'><b>OSS</b></span></td>"+
    "<td width='5%' align='right' valign='top' >"+
    "<span class='fontStyle style2 style9'><b>OST</b></span></td>"+
    "<td width='33%' align='right' valign='top' >"+
    "<span class='fontStyle style2 style9'><b>Total Space</b></span></td>"+
    "<td width='33%' align='right' valign='top' >"+
    "<span class='fontStyle style2 style9'><b>Free Space</b></span></td>" +
    "</tr>";

     $.get("/api/listfilesystems")
    .success(function(data, textStatus, jqXHR) 
    {
      var innerContent = "<option value=''>Select File System</option>";
      $.each(data, function(key, val)
      {
        if(key=='success' && val == true)
        {
          $.each(data, function(key1, val1) 
          {
            if(key1=='response')
            {
              $.each(val1, function(resKey, resValue) 
              {
                innerContent = innerContent + 
                "<option value="+resValue.fsname+">"+resValue.fsname+"</option>";

                $('#allFileSystemSummaryTbl')
                .dataTable(
                {
                  "aoColumns": [
                    { "sClass": 'txtleft'},
                    { "sClass": 'txtright'},
                    { "sClass": 'txtright'},
                    { "sClass": 'txtright'},
                    { "sClass": 'txtright'}
                  ],
                  "iDisplayLength":5,
                  "bRetrieve":true,
                  "bFilter":false,
                  "bLengthChange": false,
                  "bAutoWidth": true,
                  "bSort": false,
                  "bJQueryUI": true
                })
                .fnAddData([
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
    })
    .error(function(event) {

    });
     
    db_Bar_SpaceUsage_Data('false');
    db_Line_connectedClients_Data('false');
    db_LineBar_CpuMemoryUsage_Data('false');
    db_Area_ReadWrite_Data('false');
    db_Area_mdOps_Data('false');
    db_HeatMap_CPUData('cpu', 'false');
  }   
/*****************************************************************************
 *  Function to populate info on file system dashboard page
******************************************************************************/
  $("#fsSelect").change(function()
  {
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
    .success(function(data, textStatus, jqXHR)
    {
      if(data.success)
      {
        $.each(data.response, function(resKey, resValue)
        {
          if(resValue.kind.indexOf('OST')!=-1)
          {
            breadCrumbHtml  =  breadCrumbHtml + 
            "<option value="+resValue.host_address+">"+resValue.host_address+"</option>";
          }
        });
       }
    })
    .error(function(event) 
    {
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

    resetTimeInterval();

		    // 2011-10-17 19:56:58.720036  2011-10-17 19:46:58.720062
    fs_Bar_SpaceUsage_Data(fsName, startTime, endTime, "Average", "OST", spaceUsageFetchMatric, false);

    fs_Line_connectedClients_Data(fsName, startTime, endTime, "Average", clientsConnectedFetchMatric, false);

    fs_LineBar_CpuMemoryUsage_Data(fsName, startTime, endTime, "Average", "OST", cpuMemoryFetchMatric, false);

    fs_Area_ReadWrite_Data(fsName, startTime, endTime, "Average", "OST", readWriteFetchMatric, false);

    fs_Area_mdOps_Data(fsName, startTime, endTime, "Average", "MDT", mdOpsFetchmatric, false);

    fs_HeatMap_CPUData('cpu', 'false');

    clearInterval(dashboardPollingInterval);

    loadFileSystemSummary(fsName);
   
    $('#ls_filesystem').attr("value",fsName);
    window.location.hash =  "fs";
   
  }
/*******************************************************************************
 * Function to populate info on oss dashboard page
********************************************************************************/
  $("#ossSelect").live('change', function ()
  {
    if($(this).val()!="")
    {
      loadOSSContent($('#ls_filesystem').val(), $(this).val());
    }	
  });
		
  loadOSSContent = function(fsName, ossName)
  {
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
    .success(function(data, textStatus, jqXHR) 
    {
      if(data.success)
      {
        $.each(data.response, function(resKey, resValue)
        {
          if(resValue.kind=='OST')
          {
            breadCrumbHtml  =  breadCrumbHtml + 
            "<option value="+resValue.name+">"+resValue.name+"</option>";
          }
        });
      }
    })
    .error(function(event) 
    {
      //$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
    })
    .complete(function(event)
    {
      breadCrumbHtml = breadCrumbHtml +      	
      "</select>"+
      "</li>"+
      "</ul>";
      $("#breadCrumb2").html(breadCrumbHtml);
      $("#breadCrumb2").jBreadCrumb();
    });

    resetTimeInterval();

    oss_LineBar_CpuMemoryUsage_Data(fsName, startTime, endTime, "Average", cpuMemoryFetchMatric, 'false');

    oss_Area_ReadWrite_Data(fsName, startTime, endTime, "Average", "OST", readWriteFetchMatric, 'false');

    loadOSSUsageSummary(fsName);
	        
    $('#ls_oss').attr("value",ossName);
    window.location.hash =  "oss";

  }
/*******************************************************************************
 * Function to populate info on ost dashboard page
********************************************************************************/
  $("#ostSelect").live('change', function ()
  {
    if($(this).val()!="")
    {
      loadOSTContnent($('#ls_filesystem').val(), $('#ls_oss').val(), $(this).val());
    }	
  });

  loadOSTContnent = function(fsName, ossName, ostName)
  {
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

    resetTimeInterval();

		/* HYD-375: ostSelect value is a name instead of an ID */
    load_resource_graph("ost_resource_graph_canvas", ostName);

    ost_Pie_Space_Data(ostName, "", "", 'Average', 'OST', spaceUsageFetchMatric, 'false');
    ost_Pie_Inode_Data(ostName, "", "", 'Average', 'OST', spaceUsageFetchMatric, 'false');
    ost_Area_ReadWrite_Data(ostName, startTime, endTime, 'Average', 'OST', readWriteFetchMatric, false);

    loadOSTSummary(fsName);

    $('#ls_ost').attr("value",ostName);
    window.location.hash =  "ost";
  }
/******************************************************************************
 * Function for controlling tabs on oss dashboard
******************************************************************************/				
  $(".tab_content").hide(); //Hide all content
  $("ul.tabs li:first").addClass("active").show(); //Activate first tab
  $(".tab_content:first").show(); //Show first tab content

  //On Click Event
  $("ul.tabs li").click(function() 
  {
    $("ul.tabs li").removeClass("active"); //Remove any "active" class
    $(this).addClass("active"); //Add "active" class to selected tab
    $(".tab_content").hide(); //Hide all tab content

    var activeTab = $(this).find("a").attr("href"); //Find the href attribute value to identify the active tab + content
    $(activeTab).fadeIn(); //Fade in the active ID content
    return false;
  });
/*****************************************************************************
 * Function to reload heap map on dashboard landing page
*****************************************************************************/
  $("#db_heatmap_parameter_select").change(function()
  {
    reloadHeatMap("dashboard", $(this).val(), 'false');
  });
  $("#fs_heatmap_parameter_select").change(function()
  {
    reloadHeatMap("filesystem", $(this).val(), 'false');
  });
		  
  reloadHeatMap = function(type, value, isZoom)
  {
    if(value == "cpu")
    {
      if(type=="dashboard")
      {
        if(isZoom=='true')
          $('#zoomDialog').html("");
        else
          $('#db_heatMapDiv').html("");
        
        db_HeatMap_CPUData(value, isZoom);
      }
      else
      {
        if(isZoom=='true')
          $('#zoomDialog').html("");
        else
          $('#fs_heatMapDiv').html("");
        
        fs_HeatMap_CPUData(value, isZoom);
      }
    }
    else if(value == "disk_usage")
    {
      if(type=="dashboard")
      {
        if(isZoom=='true')
          $('#zoomDialog').html("");
        else
          $('#db_heatMapDiv').html("");
        
        db_HeatMap_ReadWriteData(value, isZoom);
      }
      else
      {
        if(isZoom=='true')
          $('#zoomDialog').html("");
        else
          $('#fs_heatMapDiv').html("");
        
        fs_HeatMap_ReadWriteData(value, isZoom);
      }
    }
    else if(value == "disk_space_usage")
    {
      if(type=="dashboard")
      {
        if(isZoom=='true')
          $('#zoomDialog').html("");
        else
          $('#db_heatMapDiv').html("");
        
        db_HeatMap_ReadWriteData(value, isZoom);
      }
      else
      {
        if(isZoom=='true')
          $('#zoomDialog').html("");
        else
          $('#fs_heatMapDiv').html("");
        
        fs_HeatMap_ReadWriteData(value, isZoom);
      }
     }
   }
/******************************************************************************
 * Function to show zoom popup dialog
******************************************************************************/  
  $('#zoomDialog').dialog
  ({
    autoOpen: false,
    width: 800,
    height:490,
    show: "clip",
    modal: true,
    position:"center",
    buttons: 
    {
      "Close": function() { 
        $(this).dialog("close");
      },
    }
  });
/******************************************************************************/
});			// End Of document.ready funtion
