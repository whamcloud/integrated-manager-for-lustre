var ERR_COMMON_DELETE_HOST = "Error in deleting host: ";
var ERR_COMMON_LNET_STATUS = "Error in setting lnet status: ";
var ERR_COMMON_ADD_HOST = "Error in Adding host: ";
var ERR_COMMON_FS_START = "Error in starting File System: ";
var ERR_COMMON_CREATE_OST = "Error in Creating OST: ";
var ERR_COMMON_CREATE_MGT = "Error in Creating MGT: ";
var ERR_COMMON_CREATE_MDT = "Error in Creating MDT: ";
var ERR_COMMON_START_OST = "Error in Starting OST: ";

var ALERT_TITLE = "Configuration Manager";
var CONFIRM_TITLE = "Configuration Manager";

RemoveHost_ServerConfig = function (host_id)
{
  $.post("/api/remove_host/",{"hostid":host_id}).success(function(data, textStatus, jqXHR) {
      if(data.success)
      {
        var response = data.response;    
        if(response.status != "")
        {
          jAlert("Host " + response.hostid + " Deleted", ALERT_TITLE);
          $('#server_configuration').dataTable().fnClearTable();
          LoadServerConf_ServerConfig();
        }
        else
        {
          jAlert(ERR_COMMON_DELETE_HOST,ALERT_TITLE);
        }
      }
      else
      {
        jAlert(ERR_COMMON_DELETE_HOST + data.errors, ALERT_TITLE);
      }
    })
    .error(function(event) {
        jAlert(ERR_COMMON_DELETE_HOST + data.errors,ALERT_TITLE);
    })
    .complete(function(event) {
    });
}

function Lnet_Operations(host_id, opps, confirm_mesg)
{
  jConfirm(confirm_mesg,"Configuration Manager", 
  function(r)
  {
    if(r == true)
    {
      //Lnet_Operations("+  resValue.id +",&apos;lnet_down&apos;);
      $.post("/api/set_lnet_state/",{"hostid":host_id, "state":opps}).success(function(data, textStatus, jqXHR) {
      if(data.success)
      {
        var response = data.response;    
        if(response.status != "")
        {
          $('#server_configuration').dataTable().fnClearTable();
          LoadServerConf_ServerConfig();
        }
        else
        {
          alert(ERR_COMMON_LNET_STATUS, ALERT_TITLE);
        }
      }
      else
      {
        jAlert(ERR_COMMON_LNET_STATUS + data.errors, ALERT_TITLE);
      }
    })
    .error(function(event) {
         jAlert(ERR_COMMON_LNET_STATUS + data.errors, ALERT_TITLE);
      })
    .complete(function(event) {
    });
    }
  });
}

function Add_Host_Table(dialog_id)
{
  //$('#host_status').remove();
  $('#status_tab').empty();
  $('#host_status').empty();
  var oTable = "<table width='100%' border='0' cellspacing='0' cellpadding='0' id='hostdetails'><tr><td width='41%' align='right' valign='middle'>Host name:</td><td width='60%' align='left' valign='middle'><input type='text' name='txtHostName' id='txtHostName' /></td></tr></table>";
  $("#" + dialog_id).dialog("option", "buttons", null);
      
      $("#" + dialog_id).dialog({ 
        buttons: { 
          "Close": function() { 
                $(this).dialog("close");
              },
          "Continue": function() { 
            AddHost_ServerConfig($('#txtHostName').val(),dialog_id); 
          } 
        }
      });
      
  $('#hostdetails_container').html(oTable);
}

function StartFileSystem(filesystem)
{
  $.post("/api/start_filesystem/",{"filesystem":filesysme}).success(function(data, textStatus, jqXHR) {
    if(data.success)
    {
      var response = data.response;    
    }
  })
  .error(function(event) {
       jAlert(ERR_COMMON_FS_START + data.errors, ALERT_TITLE);
    })
  .complete(function(event) {
  });
}

function StopFileSystem(filesystem)
{
  $.post("/api/stop_filesystem/",{"filesystem":filesysme}).success(function(data, textStatus, jqXHR) {
    if(data.success)
    {
      var response = data.response;    
    }
  })
  .error(function(event) {
       jAlert(ERR_COMMON_FS_START + data.errors, ALERT_TITLE);
    })
  .complete(function(event) {
  });
}

function CreateFS(fsname, mgt_id, mgt_lun_id, mdt_lun_id, ost_lun_ids, callback)
{
  $.ajax({type: 'POST', url: "/api/create_new_fs/", dataType: 'json', data: JSON.stringify({
      "fsname":fsname,
      "mgt_id":mgt_id,
      "mgt_lun_id":mgt_lun_id,
      "mdt_lun_id":mdt_lun_id,
      "ost_lun_ids": ost_lun_ids
    }), contentType:"application/json; charset=utf-8"})
  .success(function(data, textStatus, jqXHR) 
    {
      if(data.success)
      {
        var response = data.response;    
      }
      else
      {
         jAlert("Error", ALERT_TITLE);
      }
    })
    .error(function(event) 
    {
    })
    .complete(function(event) 
    {
      if (callback) {
        callback();
      }
    });
} 

function CreateOSTs(fsname, ost_lun_ids)
{
  $.ajax({type: 'POST', url: "/api/create_osts/", dataType: 'json', data: JSON.stringify({
      "filesystem_id": fsname,
      "ost_lun_ids": ost_lun_ids
    }), contentType:"application/json; charset=utf-8"})
    .success(function(data, textStatus, jqXHR) 
    {
      if(data.success)
      {
        var response = data.response;    
        //Reload table with latest ost's.
        LoadTargets_EditFS($("#fs_id").val());
      }
      else
      {
         jAlert("Error", ALERT_TITLE);
      }
    })
    .error(function(event) 
    {
    })
    .complete(function(event) 
    {
    });
}

function CreateMGT(lun_id, callback)
{
  $.post("/api/create_mgt/", {'lun_id': lun_id})
  .success(function(data, textStatus, jqXHR) {
    console.log(data);
    if(data.success)
    {
      callback();
    }
    else
    {
       jAlert(ERR_COMMON_CREATE_MGT, ALERT_TITLE);
    }
  })
  .error(function(event) {
  })
  .complete(function(event) {
  });
}

function SetTargetMountStage(target_id, state)
{
   $.post("/api/set_target_stage/",({"target_id": target_id, "state": state})).success(function(data, textStatus, jqXHR) 
    {
      if(data.success)
      {
        // Note: success here simply means that the operation
        // was submitted, not that it necessarily completed (that
        // happens asynchronously)
      }
      else
      {
         jAlert(ERR_COMMON_START_OST + data.errors, ALERT_TITLE);
      }
    })
    .error(function(event) 
    {
    })
    .complete(function(event) 
    {
    });
}
