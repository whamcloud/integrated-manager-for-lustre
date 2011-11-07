//confirmation dialog messages
var MSG_STOP_HOST = "Are you sure you want to stop this host?";
var MSG_START_HOST = "Are you sure you want to start host?";
var MSG_REMOVE_HOST = "Are you sure you want to remove host?";
var MSG_UNLOAD_LNET = "Lnet will be unloaded, Are you sure?";
var MSG_LOAD_LNET = "Are you sure you want to load lnet?";
var MSG_START_FSLIST = "This is will start Filesystem, Are you sure?";
var MSG_STOP_FSLIST = "Are you sure you want to stop filesystem?";
var MSG_REMOVE_FSLIST = "Are you sure you want to remove filesystem?";
var MSG_MGT_START = "Are you sure you want to start MGT?";
var MSG_MGT_STOP = "Are you sure you want to stop MGT?";
var MSG_MGT_REMOVE = "Are you sure you want to Remove MGT?";
//Error dialog messages
var ERR_FSLIST_LOAD = "Error occured in loading Filesystem: ";
var ERR_EDITFS_MGT_LOAD = "Error occured in loading MGT: ";
var ERR_EDITFS_MDT_LOAD = "Error occured in loading MDT: ";
var ERR_EDITFS_OST_LOAD = "Error occured in loading OST: ";
var ERR_COMMON_VOLUME_LOAD = "Error occured in loading volume details: ";
var ERR_SERVER_CONF_LOAD = "Error occured in loading Servers: ";
var ERR_EDITFS_FSDATA_LOAD = "Error occured in loading File system data: ";

// Create New Fs view Array for holding the usable luns selected in pop up
var ost_index = 0;
var filesystemId="";

target_dialog_link = function(target_id, target_name) {
  return "<a href='#' class='target target_id_" + target_id + "'>" + target_name + "</a>"
}


/******************************************************************
* Function name - LoadFSList_FSList()
* Param - none
* Return - none
* Used in - File System list (lustre_fs_configuration.html)
*******************************************************************/
function LoadEditFSScreen(fs_name, fs_id)
{
  $('#lustreFS_content').empty();
  $('#lustreFS_content').load('/hydracm/editfs?fs_name=' + fs_name + '&fs_id=' + fs_id);
}

function LoadFSList_FSList()
{
  $.get("/api/listfilesystems/").success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      var fsName;
      $.each(response, function(resKey, resValue)
      {
      fsName = "<a href='#' onclick=LoadEditFSScreen('" + resValue.fsname + "','" + resValue.fsid +"')>" + resValue.fsname + "</a>";
      $('#fs_list').dataTable().fnAddData ([
        fsName,
        resValue.mgs_hostname,
        resValue.mds_hostname,
        resValue.noofoss,
        resValue.noofost,
        resValue.kbytesused,
        resValue.kbytesfree,
        CreateActionLink(resValue.fsid, resValue.available_transitions, "SERVER")
        ]); 
      });
    }
  })
  .error(function(event)
  {
    jAlert(ERR_FSLIST_LOAD + data.errors);
  })
  .complete(function(event) 
  {
  });
}

function LoadTargets_EditFS(fs_id)
{
  $.get("/api/getvolumesdetails/",{filesystem_id:fs_id})
  .success(function(data, textStatus, jqXHR) {
    $('#ost').dataTable().fnClearTable();
    $('#mdt').dataTable().fnClearTable();
    $('#mgt_configuration_view').dataTable().fnClearTable();

    if(data.success)
    {
      var response = data.response;
      $.each(response, function(resKey, resValue)
      {
        row = [
                resValue.lun_name,
                target_dialog_link(resValue.id, resValue.human_name),
                resValue.primary_server_name,
                resValue.failover_server_name,
                resValue.active_host_name,
                CreateActionLink(resValue.id, resValue.available_transitions, "TARGET"),
                notification_icons_markup(resValue.id, resValue.content_type_id)
              ]
        if (resValue.kind == "OST") {
          $('#ost').dataTable().fnAddData (row);
        } else if (resValue.kind == "MGT") {
          $('#mgt_configuration_view').dataTable().fnAddData (row);
        } else if (resValue.kind == "MDT") {
          $('#mdt').dataTable().fnAddData (row);
        }
      });
      // After updating all table rows, update their .notification_object_icon elements
      notification_update_icons();
    }
  })
  .error(function(event)
  {
     jAlert(ERR_EDITFS_OST_LOAD + data.errors);
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadUsableVolumeList()
//Param - container for data table, select widget
//Return - none
//Used in - none
/******************************************************************/

function LoadUsableVolumeList(datatable_container, select_widget_fn)
{
  $.post("/api/get_luns/", {'category': 'usable'}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      $.each(data.response, function(resKey, volume_info)
      {
        var primaryHostname = "---"
        var failoverHostname = "---"
        $.each(volume_info.available_hosts, function(host_id, host_info) 
        {
          if (host_info.primary) 
          {
            primaryHostname = host_info.label
          }
          else if (host_info.use) 
          {
            failoverHostname = host_info.label
          }
        });
        datatable_container.dataTable().fnAddData ([
          volume_info.id,
          select_widget_fn(volume_info),
          volume_info.name,
          volume_info.size,
          volume_info.kind,
          volume_info.status,
          primaryHostname,
          failoverHostname
        ]); 
      });
    }
  })
  .error(function(event)
  {
    jAlert(ERR_COMMON_VOLUME_LOAD + data.errors);
  })
}

/******************************************************************/
//Function name - LoadUnused_VolumeConf()
//Param - none
//Return - none
//Used in - Volume Configuration (volume_configuration.html)
/******************************************************************/

function LoadUnused_VolumeConf()
{
  $.get("/api/get_luns/", {'category': 'unused'}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      $.each(data.response, function(resKey, resValue)
      {
        var blank_option = "<option value='-1'>---</option>";
        var blank_select = "<select disabled='disabled'>" + blank_option + "</select>"
        var primarySelect;
        var failoverSelect;
        var host_count = 0
        $.each(resValue.available_hosts, function(host_id, host_info) 
        {
          host_count += 1;
        });
        if (host_count == 0) 
        {
          primarySelect = blank_select
          failoverSelect = blank_select
        }
        else if (host_count == 1) 
        {
          $.each(resValue.available_hosts, function(host_id, host_info) 
          {
            primarySelect = "<select disabled='disabled'><option value='" + host_id + "'>" + host_info.label + "</option></select>";
          });
        failoverSelect = blank_select
        } 
        else 
        {
          primarySelect = "<select>";
          failoverSelect = "<select>";
          primarySelect += blank_option
          failoverSelect += blank_option
          $.each(resValue.available_hosts, function(host_id, host_info)
          {
            if (host_info.primary) 
            {
              primarySelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
            }
            else if (host_info.use) 
            {
              primarySelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
            } 
            else 
            {
              primarySelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
            }
          });
          failoverSelect += "</select>";
          primarySelect += "</select>";
        }
        $('#volume_configuration').dataTable().fnAddData ([
          resValue.name,
          primarySelect,
          failoverSelect,
          resValue.size,
          resValue.status
        ]); 
      });
    }
  })
  .error(function(event) 
  {
     jAlert(ERR_COMMON_VOLUME_LOAD + data.errors);
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadMGTConfiguration_MGTConf()
//Param - none
//Return - none
//Used in - MGT Configuration (new_mgt.html)
/******************************************************************/

function LoadMGTConfiguration_MGTConf()
{
  $.get("/api/get_mgts/").success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      var fsnames;
      if(data.response!="")
      {
        $.each(response, function(resKey, resValue)
        {
              fsnames = resValue.fs_names;
              $('#mgt_configuration').dataTable().fnAddData ([
                fsnames.toString(),
                resValue.lun_name,
                target_dialog_link(resValue.id, resValue.primary_server_name),
                resValue.failover_server_name,
                resValue.active_host_name,
                CreateActionLink(resValue.id,resValue.available_transitions[0], "SERVER"),
                notification_icons_markup(resValue.id, resValue.content_type_id)
              ]);
        });
      }
    }
  })
  .error(function(event)
  {
    jAlert(ERR_EDITFS_MGT_LOAD);
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadVolumeConf_VolumeConfig()
//Param - none
//Return - none
//Used in - Volume Configuration (volume_configuration.html)
/******************************************************************/

function LoadVolumeConf_VolumeConfig()
{
  $('#volume_configuration').dataTable().fnClearTable();
  $.post("/api/get_luns/",{"category": "usable"}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      var primaryServer;
      $.each(response, function(resKey, resValue)
      {
        primaryServer = "<select>";
        $.each(resValue.available_hosts, function(resFailoverKey, resFailoverValue)
        {
          if(resFailoverValue.label==undefined)
          {
            primaryServer = primaryServer + "<option value='volvo'>&nbsp;&nbsp;None&nbsp;&nbsp;</option>";
          }
          else
          {
            primaryServer = primaryServer + "<option value='volvo'>" + resFailoverValue.label + "</option>";
          }
          primaryServer = primaryServer + "</select>";
        });
        $('#volume_configuration').dataTable().fnAddData ([
          resValue.name,
          primaryServer,
          "",
          resValue.status,
          resValue.size
        ]); 
      });
    }
  })
  .error(function(event)
  {
    jAlert(ERR_COMMON_VOLUME_LOAD + data.errors);
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadServerConf_ServerConfig()
//Param - none
//Return - none
//Used in - Server Configuration (server_configuration.html)
/******************************************************************/

function LoadServerConf_ServerConfig()
{
  $.post("/api/listservers/",{"filesystem_id": ""}).success(function(data, textStatus, jqXHR)
  {
    $('#server_configuration').dataTable().fnClearTable();
    if(data.success)
    {
      var response = data.response;
      $.each(response, function(resKey, resValue)
      {
        $('#server_configuration').dataTable().fnAddData ([
          resValue.pretty_name,
          resValue.failnode,
          resValue.status,
          CreateActionLink(resValue.id,resValue.available_transitions, "SERVER"),
          notification_icons_markup(resValue.id, resValue.content_type_id)
        ]);
      });
      // After updating all table rows, update their .notification_object_icon elements
      notification_update_icons();
    }
  })
  .error(function(event)
  {
    jAlert(ERR_SERVER_CONF_LOAD + data.errors);
  })
  .complete(function(event) 
  {
  });
}

function CreateActionLink(id,available_transitions, kind)
{
  var ops_action="";
  var action="";
  var function_name;
  var button_class = "ui-state-default ui-corner-all";
  $.each(available_transitions, function(resKey, resValue)
  {
    if(kind == "SERVER")
    {
      if(resValue.state == "removed")
      {
        function_name = "RemoveHost_ServerConfig(\"" + MSG_REMOVE_HOST + "\"," + id + ")";
      }
      else
      {
        function_name = "Lnet_Operations("+  id + ",\"" + resValue.state + "\",\"" + MSG_LOAD_LNET + "\")";
      }
    }
    else if(kind == "TARGET")
    {
      if(resValue.state == "removed")
      {
        function_name = "RemoveHost_ServerConfig(\"" + MSG_REMOVE_HOST + "\"," + id + ")";
      }
      else
      {
        function_name = "SetTargetMountStage("+  id + ",\"" + resValue.state + "\",\"" + MSG_LOAD_LNET + "\")";
      }
    }
    /* ops_action = "<Button class='" + button_class + "'" +
    " onclick='"+ function_name + "'>" + 
    resValue.verb + "</Button>&nbsp;";
    action = action + ops_action; */
    
    ops_action = "<Button" +
    " onclick='"+ function_name + "'>" + 
    resValue.verb + "</Button>&nbsp;";
    action = action + ops_action;
  });
  return action;
}

/******************************************************************/
//Function name - LoadFSData_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function LoadFSData_EditFS()
{
  var fsname = $('#fs').val();
  $('#fs_name').html(fsname);
  var fs_id = $('#fs_id').val();
  if(fsname!="none")
  {
    $.post("/api/getfilesystem/",{"filesystem_id":fs_id}).success(function(data, textStatus, jqXHR)
    {
      if(data.success)
      {
        var response = data.response;
        var lnet_status_mesg;
        $.each(response, function(resKey, resValue)
        {
          $('#bytes_used').html(resValue.bytes_used);
          $('#bytes_total').html(resValue.bytes_total);
          $('#inodes_used').html(resValue.inodes_used);
          $('#inodes_total').html(resValue.inodes_total);
          $('#oss_count').html(resValue.noofoss);
          $('#ost_count').html(resValue.noofost);
          $('#mgs_name').html(resValue.mgs_hostname);
          $('#mds_name').html(resValue.mds_hostname);
          $('#fs_status').html(resValue.status);
          console.log(alert_indicator_large_markup(resValue.id, resValue.content_type_id));
          console.log($('#fs_alerts'))
          $('#fs_alerts').html(alert_indicator_large_markup(resValue.id, resValue.content_type_id));
        });
      }
    })
    .error(function(event)
    {
      jAlert(ERR_EDITFS_FSDATA_LOAD+ data.errors);
    })
    .complete(function(event) 
    {
    });
  }
}

