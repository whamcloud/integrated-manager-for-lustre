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
 * 11) loadFSContent(fsId)
 * 12) $("#ossSelect").live('change');
 * 13) loadOSSContent(fsId, fsName, ossId, ossName);
 * 14) $("#ostSelect").live('change');
 * 15) loadOSTContent(fsId, fsName, ossName, ostId, ostName);
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
       loadFSContent($('#ls_fsId').val(), $('#ls_fsName').val());
       break;
     case "#oss":
       window.location.hash =  "oss";
       loadOSSContent($('#ls_fsId').val(), $('#ls_fsName').val(), $('#ls_ossId').val(), $('#ls_ossName').val());
       break;
     case "#ost":
       window.location.hash =  "ost";
       loadOSTContent($('#ls_fsId').val(), $('#ls_fsName').val(), $('#ls_ossName').val(), $('#ls_ostId').val(), $('#ls_ostName').val(), $('#ls_ostKind').val());
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
    setStartEndTime($(this).prev('font').prev('select').find('option:selected').val(), $(this).find('option:selected').val(), "");
  });
  
  $("input[id *= polling_element]").click(function()
  {
    if($(this).is(":checked"))
    {
      isPollingFlag = true;
      initiatePolling();
    }
    else
    {
      isPollingFlag = false;
      clearAllIntervals();
    }
  });
		
  setStartEndTime = function(timeFactor, startTimeValue, endTimeValue)
  {
    endTime = endTimeValue;
		
    if(timeFactor == "minutes")
      startTime = startTimeValue;
    else if(timeFactor == "hour")
      startTime = startTimeValue * (60);
    else if(timeFactor == "day")
      startTime = startTimeValue * (24 * 60);
    else if(timeFactor == "week")
      startTime = startTimeValue * (7 * 24 * 60);

    if(! $('#dashboardDiv').is(':hidden'))
      loadLandingPageGraphs();
    else if(! $('#fileSystemDiv').is(':hidden'))
      loadFileSytemGraphs();
    else if(! $('#ossInfoDiv').is(':hidden'))
      loadServerGraphs();
    else if(! $('#ostInfoDiv').is(':hidden'))
      loadTargetGraphs();
  }

  initiatePolling = function(){
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
                "<option value="+resValue.fsid+">"+resValue.fsname+"</option>";

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
    db_AreaSpline_ioOps_Data('false');

    setActiveMenu('dashboard_menu');
  }   
/*****************************************************************************
 *  Function to populate info on file system dashboard page
******************************************************************************/
  $("#fsSelect").change(function()
  {
    if($(this).val()!="")
    {
      loadFSContent($(this).val(), $(this).find('option:selected').text());
    }
  });         

  loadFSContent = function(fsId, fsName)
  {
    $('#dashboardDiv').hide();$('#ossInfoDiv').hide();$('#ostInfoDiv').hide();
    $('#fileSystemDiv').slideDown("slow");
    var breadCrumbHtml = "<ul>"+
    "<li><a href='/dashboard'>Home</a></li>"+
    "<li><a href='/dashboard'>All FileSystems</a></li>"+
    "<li>"+fsName+"</li>"+
    "<li>"+
    "<select id='ossSelect'>"+
    "<option value=''>Select Server</option>";

    $.post("/api/listservers/",{filesystem_id:fsId}) 
    .success(function(data, textStatus, jqXHR)
    {
      if(data.success)
      {
        $.each(data.response, function(resKey, resValue)
        {
          breadCrumbHtml += "<option value="+resValue.id+">" + resValue.pretty_name + "</option>";
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
    fs_Bar_SpaceUsage_Data(fsId, startTime, endTime, "Average", "OST", spaceUsageFetchMatric, false);

    fs_Line_connectedClients_Data(fsId, startTime, endTime, "Average", clientsConnectedFetchMatric, false);

    fs_LineBar_CpuMemoryUsage_Data(fsId, startTime, endTime, "Average", "OST", cpuMemoryFetchMatric, false);

    fs_Area_ReadWrite_Data(fsId, startTime, endTime, "Average", "OST", readWriteFetchMatric, false);

    fs_Area_mdOps_Data(fsId, startTime, endTime, "Average", "MDT", mdOpsFetchmatric, false);

    fs_AreaSpline_ioOps_Data('false');

    clearAllIntervals();

    loadFileSystemSummary(fsId);
   
    $('#ls_fsId').attr("value",fsId);$('#ls_fsName').attr("value",fsName);
    window.location.hash =  "fs";
   
  }
/*******************************************************************************
 * Function to populate info on oss dashboard page
********************************************************************************/
  $("#ossSelect").live('change', function ()
  {
    if($(this).val()!="")
    {
      loadOSSContent($('#ls_fsId').val(), $('#ls_fsName').val(), $(this).val(), $(this).find('option:selected').text());
    }	
  });
		
  loadOSSContent = function(fsId, fsName, ossId, ossName)
  {
    $('#dashboardDiv').hide();$('#fileSystemDiv').hide();$('#ostInfoDiv').hide();
    $('#ossInfoDiv').slideDown("slow");
    var ostKindMarkUp = "<option value=''></option>";
    
    var breadCrumbHtml = "<ul>"+
    "<li><a href='/dashboard'>Home</a></li>"+
    "<li><a href='/dashboard'>All FileSystems</a></li>"+
    "<li><a href='#fs' onclick='showFSDashboard()'>"+fsName+"</a></li>"+
    "<li>"+ossName+"</li>"+
    "<li>"+
    "<select id='ostSelect'>"+
    "<option value=''>Select Target</option>";
    
    $.ajax({type: 'POST', url: "/api/get_fs_targets/", dataType: 'json', data: JSON.stringify({
      "filesystem_id": fsId,
      "kinds": ["OST","MGT","MDT"],
      "host_id": ossId
    }), contentType:"application/json; charset=utf-8"})
    .success(function(data, textStatus, jqXHR) 
    {
      var targets = data.response;
      targets = targets.sort(function(a,b) {return a.label > b.label;})

      var count = 0;
      $.each(targets, function(i, target_info) {
        breadCrumbHtml += "<option value='" + target_info.id + "'>" + target_info.label + "</option>"
        
        ostKindMarkUp = ostKindMarkUp + "<option value="+target_info.id+">"+target_info.kind+"</option>";
        
        count += 1; 
      });
    })
    .error(function(event) 
    {
    })
    .complete(function(event)
    {
      breadCrumbHtml = breadCrumbHtml +      	
      "</select>"+
      "</li>"+
      "</ul>";
      $("#breadCrumb2").html(breadCrumbHtml);
      $("#breadCrumb2").jBreadCrumb();
      
      $("#ostKind").html(ostKindMarkUp);
    });

    resetTimeInterval();

    oss_LineBar_CpuMemoryUsage_Data(ossId, startTime, endTime, "Average", cpuMemoryFetchMatric, 'false');

    oss_Area_ReadWrite_Data(fsId, startTime, endTime, "Average", "OST", readWriteFetchMatric, 'false');

    loadOSSUsageSummary(fsId);
    
    clearAllIntervals();
	        
    $('#ls_ossId').attr("value",ossId);$('#ls_ossName').attr("value",ossName);
    window.location.hash =  "oss";
  }
/*******************************************************************************
 * Function to populate info on ost dashboard page
********************************************************************************/
  $("#ostSelect").live('change', function ()
  {
    if($(this).val()!="")
    {
      $("#ostKind").attr("value",$(this).val());
      var ostKind = $("#ostKind").find('option:selected').text();
      
      loadOSTContent($('#ls_fsId').val(), $('#ls_fsName').val(), $('#ls_ossName').val(), $(this).val(), $(this).find('option:selected').text(), ostKind);
    }	
  });

  loadOSTContent = function(fsId, fsName, ossName, ostId, ostName, ostKind)
  {
    $('#dashboardDiv').hide();$('#fileSystemDiv').hide();$('#ossInfoDiv').hide();
    $('#ostInfoDiv').slideDown("slow");
    var breadCrumbHtml = "<ul>"+
    "<li><a href='/dashboard'>Home</a></li>"+
    "<li><a href='/dashboard'>All FileSystems</a></li>"+
    "<li><a href='#fs' onclick='showFSDashboard()'>"+fsName+"</a></li>"+
    "<li><a href='#oss' onclick='showOSSDashboard()'>"+ossName+"</a></li>"+
    "<li>"+ostName+"</li>"+
    "</ul>";

    $("#breadCrumb3").html(breadCrumbHtml);
    $("#breadCrumb3").jBreadCrumb();

    resetTimeInterval();

		$('#ls_ostId').attr("value",ostId);$('#ls_ostName').attr("value",ostName);$('#ls_ostKind').attr("value",ostKind);
    window.location.hash =  "ost";
    
    clearAllIntervals();
    
    loadOSTSummary(fsId);
    
    loadTargetGraphs();
    
    /* HYD-375: ostSelect value is a name instead of an ID */
    load_resource_graph("ost_resource_graph_canvas", ostId);
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
});			// End Of document.ready funtion
