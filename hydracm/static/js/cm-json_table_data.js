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

function notification_icon_markup(id, ct) {
  return "<span class='notification_object_icon notification_object_id_" + id + "_" + ct + "'/>"
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
      var action; 
      $.each(response, function(resKey, resValue)
      {
      fsName = "<a href='#' onclick=LoadEditFSScreen('" + resValue.fsname + "','" + resValue.fsid +"')>" + resValue.fsname + "</a>";
      action = "<a href='#' onclick='jConfirm(\"" + MSG_START_FSLIST + "\",\"Configuration Manager\", function(r){if(r == true){StartFileSystem(\""+  resValue.fsname +"\");}});'>Start<img src='/static/images/start.png' height=12 width=12 title='Start'/></a> | <a href='#'>Configuration<img src='/static/images/configuration.png' height=15 width=15 title='Configuration Param'/></a> | <a href='#' onclick='jConfirm(\"" + MSG_REMOVE_FSLIST + "\",\"Configuration Manager\", function(r){if(r == true){StartFileSystem(\""+  resValue.fsname +"\");}});'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
      $('#fs_list').dataTable().fnAddData ([
        fsName,
        resValue.mgs_hostname,
        resValue.mds_hostname,
        resValue.noofoss,
        resValue.noofost,
        resValue.kbytesused,
        resValue.kbytesfree,
        action
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
        if(resValue.state == "mounted")
        {
          message = "Are you sure you want to stop " + resValue.human_name + "?";
          action = "<a href='#' onclick='jConfirm(\"" + message + "\",\"Configuration Manager\", function(r){if(r == true){SetTargetMountStage(\""+  resValue.id +"\",\"unmounted\");}});'>Stop<img src='/static/images/stop.png' title='Stop' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>"; 
        }
        else if (resValue.state == 'unmounted')
        {
          message = "Are you sure you want to start " + resValue.human_name + "?";
          action = "<a href='#' onclick='jConfirm(\"" + message + "\",\"Configuration Manager\", function(r){if(r == true){SetTargetMountStage(\""+  resValue.id +"\",\"mounted\");}});'>Start<img src='/static/images/start.png'title='Start' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
        }
        else
        {
          action = ""
        }
        row = [
                resValue.lun_name,
                resValue.human_name,
                resValue.primary_server_name,
                resValue.failover_server_name,
                resValue.active_host_name,
                action,
                notification_icon_markup(resValue.id, resValue.content_type_id)
              ]
        if (resValue.kind == "OST") {
          $('#ost').dataTable().fnAddData (row);
        } else if (resValue.kind == "MGT") {
          $('#mgt_configuration_view').dataTable().fnAddData (row);
        } else if (resValue.kind == "MDT") {
          $('#mdt').dataTable().fnAddData (row);
        }
      });
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
              if(resValue.state == "mounted")
              {
                action = "<a href='#'>Stop<img src='/static/images/stop.png' title='Stop' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
              }
              else
              {
                action = "<a href='#'>Start<img src='/static/images/start.png'title='Start' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
              }
              
              $('#mgt_configuration').dataTable().fnAddData ([
                fsnames.toString(),
                resValue.lun_name,
                resValue.primary_server_name,
                resValue.failover_server_name,
                resValue.active_host_name,
                action
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
      var lnet_status_mesg;
      var lnet_status;
      $.each(response, function(resKey, resValue)
      {
        lnet_status = resValue.lnet_status;
        lnet_status_mesg="";
        if(lnet_status == "lnet_up")
        {
          lnet_status_mesg = "<a href='#' onclick='Lnet_Operations("+  resValue.id +",&apos;lnet_down&apos;,&apos;"+ MSG_STOP_HOST+ "&apos;)'>Stop<img src='/static/images/stop.png' title='Stop Lnet' height=15 width=15 /></a> | <a href='#' onclick='jConfirm(\"" + MSG_REMOVE_HOST + "\",\"Configuration Manager\", function(r){if(r == true){RemoveHost_ServerConfig("+  resValue.id +");}});'>Remove<img src='/static/images/remove.png' title='Remove' height=15 width=15 id='"+ resValue.id +"'/></a> | <a href='#' onclick='Lnet_Operations("+  resValue.id +",&apos;lnet_unload&apos;,&apos;"+ MSG_UNLOAD_LNET+ "&apos;)'>Unload<img src='/static/images/unload.png' title='Unload Lnet' height=15 width=15 /></a> | <a href='#'>Configuration<img src='/static/images/configuration.png' title='Configuration' height=15 width=15/></a>";
        }
        else if(resValue.lnet_status == "lnet_down")
        {
          lnet_status_mesg = "<a href='#' onclick='Lnet_Operations("+  resValue.id +",&apos;lnet_up&apos;,&apos;"+ MSG_START_HOST + "&apos;)'>Start<img src='/static/images/start.png' title='Start Lnet' height=15 width=15 /></a> | <a href='#' onclick='jConfirm(\"" + MSG_REMOVE_HOST + "\",\"Configuration Manager\", function(r){if(r == true){RemoveHost_ServerConfig("+  resValue.id +");}});'>Remove<img src='/static/images/remove.png' title='Remove' height=15 width=15 id='"+ resValue.id +"'/></a> | <a href='#' onclick='Lnet_Operations("+  resValue.id +",&apos;lnet_down&apos;,&apos;"+ MSG_UNLOAD_LNET + "&apos;)'>Unload<img src='/static/images/unload.png' title='Unload Lnet' height=15 width=15 /></a> | <a href='#'>Configuration<img src='/static/images/configuration.png' title='Configuration' height=15 width=15/></a>"; 
        }
        else if(resValue.lnet_status == "lnet_unloaded")
        {
          lnet_status_mesg = "<a href='#' onclick='Lnet_Operations("+  resValue.id +",&apos;lnet_up&apos;,&apos;"+ MSG_START_HOST + "&apos;)'>Start<img src='/static/images/start.png' title='Start Lnet' height=15 width=15 /></a> | <a href='#' onclick='jConfirm(\"" + MSG_REMOVE_HOST + "\",\"Configuration Manager\", function(r){if(r == true){RemoveHost_ServerConfig("+  resValue.id +");}});'>Remove<img src='/static/images/remove.png' title='Remove' height=15 width=15 id='"+ resValue.id +"'/></a> | &nbsp;&nbsp;<a href='#' onclick='Lnet_Operations("+  resValue.id +",&apos;lnet_load&apos;,&apos;"+ MSG_LOAD_LNET + "&apos;)'>Load<img src='/static/images/load.png' title='Load Lnet' height=15 width=15 /></a>&nbsp;&nbsp; | <a href='#'>Configuration<img src='/static/images/configuration.png' title='Configuration' height=15 width=15/></a>";  
        }
        $('#server_configuration').dataTable().fnAddData ([
          resValue.host_address,
          resValue.failnode,
          resValue.status,
          lnet_status,
          lnet_status_mesg,
          notification_icon_markup(resValue.id, resValue.content_type_id)
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

/******************************************************************/
//Function name - LoadFSData_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function LoadFSData_EditFS()
{
  var fsname = $('#fs').val();
  $('#txtfsnameid').val(fsname);
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
          $('#total_capacity').html(resValue.kbytesused);
          $('#total_free').html(resValue.kbytesfree);
          $('#mdt_file_used').html(resValue.filestotal);
          $('#mdt_file_free').html(resValue.filesfree);
          $('#total_oss').html(resValue.noofoss);
          $('#total_ost').html(resValue.noofost);
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

