/*******************************************************************************
 * File name: custom_dasboard.js
 * Description: Common functions required by dashboard
 * ------------------ Data Loader functions--------------------------------------
 * 1) loadView(key)
 * 2) load_breadcrumbs
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
 * 17) $("#heatmap_parameter_select").change();
 * 18) reloadHeatMap(fetchmetric);
/*****************************************************************************/
var server_list_content = "";

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
    $("#fsSelect").attr("value", $("#ls_fsId").val());
    $("#serverSelect").attr("value", $("#ls_ossId").val());
  }
/******************************************************************************
 * Function for showing time interval units
******************************************************************************/
$(document).ready(function(){
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

  $("#db_heatmap_parameter_select").change(function()
  {
    reloadHeatMap("dashboard", $(this).val(), 'false');
  });
  $("#fs_heatmap_parameter_select").change(function()
  {
    reloadHeatMap("filesystem", $(this).val(), 'false');
  });

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



    Api.get("filesystem", {limit: 0},
      success_callback = function(data)
      {
        $('#allFileSystemSummaryTbl').dataTable({
          "aoColumns": [
                        { "sClass": 'txtleft'},
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
                    }).fnClearTable();
        
        $.each(data.objects, function(resKey, resValue) 
        {

          $('#allFileSystemSummaryTbl').dataTable().fnAddData([
            resValue.name,
            resValue.osts.length,
            formatBytes(resValue.bytes_total),
            formatBytes(resValue.bytes_free),
          ]);
        });

        populateFsSelect(data.objects)
        
        load_breadcrumbs();
      });

      chart_manager_dashboard();
      db_Bar_SpaceUsage_Data('false');
      db_Line_connectedClients_Data('false');
      //db_LineBar_CpuMemoryUsage_Data('false');
      db_Area_ReadWrite_Data('false');
      db_Area_mdOps_Data('false');
      db_AreaSpline_ioOps_Data('false');
  
      $('#dashboard_menu').addClass('active');
  }
  
  $("#selectView").live('change', function ()
  {
    showView($(this).val());
  });
  
  showView = function(view_value)
  {
    var breadCrumbHtml = "<ul style='float: left;'>"+
    "<li><a href='/dashboard'>Home</a></li>"+
    "<li>"+get_view_selection_markup()+"</li>"+
    "<li>" +
    "<select id='fsSelect' style='display:none'>"+
    "</select>" +
    "<select id='serverSelect' style='display:none'>"+
    "</select>" +
    "</li>"+
    "</ul>";
    $("#breadCrumb0").html(breadCrumbHtml);
    
    loadLandingPage();
    $('#fileSystemDiv').hide();$('#ossInfoDiv').hide();$('#ostInfoDiv').hide();
    $('#dashboardDiv').slideDown("slow");

    if(view_value == "filesystem_view")
    {
      $("#fsSelect").css("display","block");
      $("#serverSelect").css("display","none");
    }
    else if(view_value == "server_view")
    {
      server_list_content = "";
      server_list_content += "<option value=''>Select Server</option>";
      Api.get("host/", {limit: 0}, 
        success_callback = function(data)
        {
          $.each(data.objects, function(i, host)
          {
            server_list_content += "<option value="+host.id+">" + host.label + "</option>";
          });
          $("#serverSelect").html(server_list_content);
          $("#fsSelect").css("display","none");
          $("#serverSelect").css("display","block");
          
          $('#ls_fsId').attr("value", "");
          $('#ls_ossId').attr("value", "");
          
          load_breadcrumbs();
        });
    }
  }
/*****************************************************************************
 *  Function to populate info on file system dashboard page
******************************************************************************/
  $("#fsSelect").live('change', function ()
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
    var ostKindMarkUp = "<option value=''></option>";
    
    var breadCrumbHtml = "<ul>"+
    "<li><a href='/dashboard'>Home</a></li>" +
    "<li>"+get_view_selection_markup()+"</li>" +
    "<li><select id=\"fsSelect\"></select></li>" +
    "<li>"+
    "<select id='ostSelect'>"+
    "<option value=''>Select Target</option>";

    Api.get("filesystem", {limit: 0},
      success_callback = function(data) {
        populateFsSelect(data.objects);
      }
    );

    Api.get("target/", {"filesystem_id": fsId, limit: 0}, 
      success_callback = function(data)
      {
        var targets = data.objects;
        targets = targets.sort(function(a,b) {return a.label > b.label;})
  
        var count = 0;
        $.each(targets, function(i, target_info) 
        {
          breadCrumbHtml += "<option value='" + target_info.id + "'>" + target_info.label + "</option>"
  
          ostKindMarkUp = ostKindMarkUp + "<option value="+target_info.id+">"+target_info.kind+"</option>";
  
          count += 1; 
        });

        breadCrumbHtml = breadCrumbHtml +       
        "</select>"+
        "</li>"+
        "</ul>";
        $("#breadCrumb0").html(breadCrumbHtml);
        load_breadcrumbs();

        $("#ostKind").html(ostKindMarkUp);
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
  $("#serverSelect").live('change', function ()
  {
    if($(this).val()!="")
    {
      loadOSSContent($('#ls_fsId').val(), $('#ls_fsName').val(), $(this).val(), $(this).find('option:selected').text());
    }   
  });
  
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
    var ost_file_system_MarkUp = "<option value=''></option>";
    
    var breadCrumbHtml = "<ul>"+
    "<li><a href='/dashboard'>Home</a></li>"+
    "<li>"+get_view_selection_markup()+"</li>";
    if(fsId == "")
    {
      breadCrumbHtml += "<li>"+get_server_list_markup()+"</li>";
    }
    else
    {
      breadCrumbHtml +="<li><a href='#fs' onclick='showFSDashboard()'>"+fsName+"</a></li>"+
      "<li>"+ossName+"</li>";
    }
    breadCrumbHtml += "<li>"+
    "<select id='ostSelect'>"+
    "<option value=''>Select Target</option>";

    var file_systems_ids = new Array();
    var file_count = 0;
    
    Api.get("target/", {"host_id": ossId, limit: 0}, 
      success_callback = function(data)
      {
        var targets = data.objects;
        targets = targets.sort(function(a,b) {return a.label > b.label;})
  
        var count = 0;
        $.each(targets, function(i, target_info) 
        {
          breadCrumbHtml += "<option value='" + target_info.id + "'>" + target_info.label + "</option>"
          
          ostKindMarkUp = ostKindMarkUp + "<option value="+target_info.id+">"+target_info.kind+"</option>";
  
          ost_file_system_MarkUp = ost_file_system_MarkUp + "<option value="+target_info.id+">"+target_info.filesystem_id+"</option>";
          
          if(target_info.filesystem_id != null)
          {
            if(!find_file_system_id(file_systems_ids, target_info.filesystem_id))
              file_systems_ids.push(target_info.filesystem_id);
          }
  
          count += 1; 
        });
        
        breadCrumbHtml = breadCrumbHtml +      	
        "</select>"+
        "</li>"+
        "</ul>";
        $("#breadCrumb0").html(breadCrumbHtml);
        load_breadcrumbs();

        $("#ostKind").html(ostKindMarkUp);
        $("#ost_file_system").html(ost_file_system_MarkUp);
        
        $('#ossSummaryTblDiv').show();
        $('#serverSummaryTblDiv').show();
      });

    resetTimeInterval();

    oss_LineBar_CpuMemoryUsage_Data(ossId, startTime, endTime, "Average", cpuMemoryFetchMatric, 'false');

    oss_Area_ReadWrite_Data(fsId, startTime, endTime, "Average", "OST", readWriteFetchMatric, 'false');

    clearAllIntervals();

    $('#ls_ossId').attr("value",ossId);$('#ls_ossName').attr("value",ossName);
    window.location.hash =  "oss";
  }
  
  find_file_system_id = function(file_systems_ids, file_system_id)
  {
    for(var x=0; x<file_systems_ids.length; x++)
    {
      if(file_systems_ids[x] == file_system_id)
      {
        return true;
      }
    }
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
      
      if($('#ls_fsId').val() == "")
      {
        $("#ost_file_system").attr("value",$(this).val());
      }
      
      loadOSTContent($('#ls_fsId').val(), $('#ls_fsName').val(), $('#ls_ossName').val(), $(this).val(), $(this).find('option:selected').text(), ostKind);
    }	
  });

  loadOSTContent = function(fsId, fsName, ossName, ostId, ostName, ostKind)
  {
    $('#dashboardDiv').hide();$('#fileSystemDiv').hide();$('#ossInfoDiv').hide();
    $('#ostInfoDiv').slideDown("slow");
    var breadCrumbHtml = "<ul>"+
    "<li><a href='/dashboard'>Home</a></li>"+
    "<li>"+get_view_selection_markup()+"</li>";
    if(fsId == "")
    {
      breadCrumbHtml += "<li><a href='#oss' onclick='showOSSDashboard()'>"+ossName+"</a></li>";
      fsId =  $("#ost_file_system").find('option:selected').text();
    }
    else
    {
      breadCrumbHtml += "<li><a href='#fs' onclick='showFSDashboard()'>"+fsName+"</a></li>";
      //"<li><a href='#oss' onclick='showOSSDashboard()'>"+ossName+"</a></li>";
    }
    
    breadCrumbHtml += "<li>"+ostName+"</li>"+
    "</ul>";

    $("#breadCrumb0").html(breadCrumbHtml);
    load_breadcrumbs();

    resetTimeInterval();

    $('#ls_ostId').attr("value",ostId);$('#ls_ostName').attr("value",ostName);$('#ls_ostKind').attr("value",ostKind);
    window.location.hash =  "ost";
    
    clearAllIntervals();
    
    if(fsId > 0)
    {
      loadOSTSummary(fsId);
    }
    else
    {
      $('#ostSummaryTbl').html("");
    }
    
    loadTargetGraphs();
    
    /* HYD-375: ostSelect value is a name instead of an ID */
    load_resource_graph("ost_resource_graph_canvas", ostId);
  }

/*****************************************************************************
 * Function to reload heap map on dashboard landing page
*****************************************************************************/

		  
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
 * Function to get markup for breadcrumb view selection
******************************************************************************/
  get_view_selection_markup = function()
  {
    var view_selection_markup = "<select id='selectView'>";
    if($("#selectView").val() == "filesystem_view")
      view_selection_markup += "<option value='filesystem_view' selected>File System View</option>";
    else
      view_selection_markup += "<option value='filesystem_view'>File System View</option>";
    
    if($("#selectView").val() == "server_view")
      view_selection_markup += "<option value='server_view' selected>Server View</option>";
    else
      view_selection_markup += "<option value='server_view'>Server View</option>";
    
    view_selection_markup += "</select>";
    return view_selection_markup;
  }
  
  get_server_list_markup = function()
  {
    var server_list_markup = "<select id='serverSelect'>";
    server_list_markup += server_list_content;
    server_list_markup += "</select>";
    return server_list_markup;
  }

function populateFsSelect(filesystems)
{
  var filesystem_list_content = "";
  $.each(filesystems, function(i, filesystem) {
    filesystem_list_content = "<option value=''>Select File System</option>";
    filesystem_list_content += "<option value="+filesystem.id+">"+filesystem.name+"</option>";
  });
  $('#fsSelect').html(filesystem_list_content);
}
