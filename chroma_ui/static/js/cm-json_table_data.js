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
function LoadFSList_FSList()
{
  invoke_api_call(api_get, "filesystem", "", 
  success_callback = function(data)
  {
    var response = data;
    var fsName;
    $('#fs_list').dataTable().fnClearTable();
    $.each(response, function(resKey, resValue)
    {
      fsName = "<a href='#filesystems_edit_" + resValue.fsid +"' class='address_link'>" + resValue.fsname + "</a>";
      $('#fs_list').dataTable().fnAddData ([
        fsName,
        resValue.mgs_hostname,
        resValue.mds_hostname,
        resValue.noofoss,
        resValue.noofost,
        resValue.kbytesused,
        resValue.kbytesfree,
        CreateActionLink(resValue.id, resValue.content_type_id, resValue.available_transitions),
        notification_icons_markup(resValue.id, resValue.content_type_id)
        ]);
    });
  });
}

function LoadTargets_EditFS(fs_id)
{
  invoke_api_call(api_get, "target/", {filesystem_id : fs_id}, 
  success_callback = function(targets)
  {  
    $('#ost').dataTable().fnClearTable();
    $('#mdt').dataTable().fnClearTable();
    $('#mgt_configuration_view').dataTable().fnClearTable();

    $.each(targets, function(i, target)
    {
      row = [
              target_dialog_link(target.id, object_name_markup(target.id, target.content_type_id, target.label)),
              target.lun_name,
              target.primary_server_name,
              target.failover_server_name,
              target.active_host_name,
              CreateActionLink(target.id, target.content_type_id, target.available_transitions),
              notification_icons_markup(target.id, target.content_type_id)
            ]
      if (target.kind == "OST") {
        $('#ost').dataTable().fnAddData (row);
      } else if (target.kind == "MGT") {
        $('#mgt_configuration_view').dataTable().fnAddData (row);
      } else if (target.kind == "MDT") {
        $('#mdt').dataTable().fnAddData (row);
      }
    });
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
  invoke_api_call(api_get, "volume/", {'category': 'usable'}, 
  success_callback = function(volumes)
  {
    $.each(volumes, function(i, volume)
    {
      var primaryHostname = "---"
      var failoverHostname = "---"
      $.each(volume.nodes, function(i, node) 
      {
        if (node.primary) 
        {
          primaryHostname = node.host_label
        }
        else if (node.use) 
        {
          failoverHostname = node.host_label
        }
      });
      datatable_container.dataTable().fnAddData ([
        volume.id,
        select_widget_fn(volume),
        volume.name,
        volume.size,
        volume.kind,
        volume.status,
        primaryHostname,
        failoverHostname
      ]); 
    });
  });
}

/******************************************************************/
//Function name - LoadUnused_VolumeConf()
//Param - none
//Return - none
//Used in - Volume Configuration (volume_configuration.html)
/******************************************************************/

function LoadUnused_VolumeConf()
{
  invoke_api_call(api_get, "volume/", {'category': 'unused'}, 
  success_callback = function(volumes)
  {
    $('#volume_configuration').dataTable().fnClearTable();
    
    $.each(volumes, function(i, volume)
    {
      var blank_option = "<option value='-1'>---</option>";
      var blank_select = "<select disabled='disabled'>" + blank_option + "</select>"
      var primarySelect;
      var failoverSelect;
      var original_mapped_node_ids = "";
      var primary_node_id = 0;
      var secondary_node_id = -1;
      var lun_id = volume.id;

      if (volume.nodes.length == 0) 
      {
        primarySelect = blank_select
        failoverSelect = blank_select
      }
      else if (volume.nodes.length == 1) 
      {
        $.each(volume.nodes, function(i, node) 
        {
          primarySelect = "<select id='primary_host_"+lun_id+"' disabled='disabled'><option value='" + node.id + "'>" + node.host_label + "</option></select>";
        });
        failoverSelect = blank_select
      } 
      else 
      {
        primarySelect = "<select id='primary_host_"+lun_id+"'>";
        failoverSelect = "<select id='secondary_host_"+lun_id+"'>";
        failoverSelect += blank_option
        $.each(volume.nodes, function(i, node)
        {
          if (node.primary) 
          {
            primarySelect += "<option value='" + node.id + "' selected='selected'>" + node.host_label + "</option>";
            failoverSelect += "<option value='" + node.id + "'>" + node.host_label + "</option>";
            primary_node_id = node.id;
          }
          else if (node.use) 
          {
            primarySelect += "<option value='" + node.id + "'>" + node.host_label + "</option>";
            failoverSelect += "<option value='" + node.id + "' selected='selected'>" + node.host_label + "</option>";
            secondary_node_id = node.id;
          } 
          else 
          {
            primarySelect += "<option value='" + node.id + "'>" + node.host_label + "</option>";
            failoverSelect += "<option value='" + node.id + "'>" + node.host_label + "</option>";
          }
        });
        failoverSelect += "</select>";
        primarySelect += "</select>";
      }

      var original_mapped_node_ids = lun_id + "_" + primary_node_id + "_" + secondary_node_id;
      var hiddenIds = original_mapped_node_ids;
      
      $('#volume_configuration').dataTable().fnAddData ([
        volume.name,
        primarySelect,
        failoverSelect,
        volume.size,
        volume.status,
        original_mapped_node_ids,
        hiddenIds
      ]); 
    });
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
  invoke_api_call(api_get, "target/", {kind: 'MGT'}, 
  success_callback = function(mgt_list)
  {
    $('#mgt_configuration').dataTable().fnClearTable();
    $.each(mgt_list, function(i, mgt)
    {
          var fs_names = [];
          $.each(mgt.filesystems, function(i, fs) {fs_names.push(fs.name);});

          $('#mgt_configuration').dataTable().fnAddData ([
            fs_names.join(", "),
            mgt.lun_name,
            target_dialog_link(mgt.id, mgt.primary_server_name),
            mgt.failover_server_name,
            mgt.active_host_name,
            CreateActionLink(mgt.id, mgt.content_type_id, mgt.available_transitions),
            notification_icons_markup(mgt.id, mgt.content_type_id)
          ]);
    });
  })
}



