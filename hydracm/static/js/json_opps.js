var ERR_COMMON_DELETE_HOST = "Error in deleting host: ";
var ERR_COMMON_LNET_STATUS = "Error in setting lnet status: ";
var ERR_COMMON_ADD_HOST = "Error in Adding host: ";
var ERR_COMMON_FS_START = "Error in starting File System: ";
var ERR_COMMON_CREATE_OST = "Error in Creating OST: ";
var ERR_COMMON_CREATE_MGT = "Error in Creating MGT: ";
var ERR_COMMON_CREATE_MDT = "Error in Creating MDT: ";
RemoveHost_ServerConfig = function (host_id)
{
  $.post("/api/remove_host/",{"hostid":host_id}).success(function(data, textStatus, jqXHR) {
      if(data.success)
      {
        var response = data.response;    
        if(response.status != "")
        {
          jAlert("Host " + response.hostid + " Deleted");
          $('#server_configuration').dataTable().fnClearTable();
          LoadServerConf_ServerConfig();
        }
        else
        {
          jAlert(ERR_COMMON_DELETE_HOST);
        }
      }
      else
      {
        jAlert(ERR_COMMON_DELETE_HOST + data.errors);
      }
    })
    .error(function(event) {
        jAlert(ERR_COMMON_DELETE_HOST + data.errors);
    })
    .complete(function(event) {
    });
}

function Lnet_Operations(host_id, opps)
{
  $.post("/api/set_lnet_state/",{"hostid":host_id, "state":opps}).success(function(data, textStatus, jqXHR) {
    if(data.success)
    {
      var response = data.response;    
      if(response.status != "")
      {
        jAlert("Host Lnet State changed to " + opps);
        $('#server_configuration').dataTable().fnClearTable();
        LoadServerConf_ServerConfig();
      }
      else
      {
        alert(ERR_COMMON_LNET_STATUS);
      }
    }
    else
    {
      jAlert(ERR_COMMON_LNET_STATUS + data.errors);
    }
  })
  .error(function(event) {
       jAlert(ERR_COMMON_LNET_STATUS + data.error);
    })
  .complete(function(event) {
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
       jAlert(ERR_COMMON_FS_START + data.errors);
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
       jAlert(ERR_COMMON_FS_START + data.errors);
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
        jAlert("Success");
      }
      else
      {
         jAlert("Error");
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

function CreateFSOSSs(fsname,ost_id)
{
  alert("/api/create_osts/{'filesystem_id':" + fsname + "'ost_node_ids':" + GetOSTId(ost_id) + "'failover_ids':''");
  $.post("/api/create_osts/",({"filesystem_id": fsname, "ost_node_ids": GetOSTId(ost_id),"failover_ids": ''})).success(function(data, textStatus, jqXHR) 
    {
      if(data.success)
      {
        var response = data.response;    
        jAlert("Success");
      }
      else
      {
         jAlert("Error");
      }
    })
    .error(function(event) 
    {
    })
    .complete(function(event) 
    {
    });
    //Reset ost array
    arrOSS_Id=[];
}

function CreateMGTs(ost_id)
{
  for(var i=0;i<arrOSS_Id.length;i++)
  {
    alert("/api/create_mgt/{'nodeid:" + arrOSS_Id[i] + "'failoverid':''");
    $.post("/api/create_osts/",({"nodeid": arrOSS_Id[i], "failoverid" :''})).success(function(data, textStatus, jqXHR) 
    {
      if(data.success)
      {
        var response = data.response;    
        jAlert("Success");
      }
      else
      {
         jAlert("Error");
      }
    })
    .error(function(event) {
    })
    .complete(function(event) {
    });
  }
  //Reset ost array
  arrOSS_Id=[];
}

function GetOSTId(arrOST)
{
  var ost_id="";
  for(var i=0;i<arrOST.length;i++)
  {
    if (ost_id == "")
    {
     ost_id = arrOST[i];
    }
    else
    {
      ost_id = ost_id + "," + arrOST[i];
    }
  }
  return ost_id;
}
