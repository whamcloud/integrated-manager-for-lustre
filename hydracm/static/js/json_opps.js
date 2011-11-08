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

TransitionCommit = function(id, ct, state)
{
  $.post("/api/transition/",{id: id, content_type_id: ct, new_state: state})
   .success(function(data, textStatus, jqXHR) {
    if(data.success) {
    } else {
        /* Generic server comms error */
    }
    })
    .error(function(event) {
        /* Generic server comms error */
    })
}

$(document).ready(function() {
  $('#transition_confirmation_dialog').dialog({autoOpen: false, maxHeight: 400, maxWidth: 800, width: 'auto', height: 'auto'});
});

Transition = function (id, ct, state)
{
  $.post("/api/transition_consequences/", {id: id, content_type_id: ct, new_state: state})
   .success(function(data, textStatus, jqXHR) {
     var requires_confirmation = false;
     if (data.success) {
       var confirmation_markup = "<p>This action will have the following consequences:</p><ul>";
       if (data.response.length > 1) {
       $.each(data.response, function(i, consequence_info) {
         confirmation_markup += "<li>" + consequence_info.description + "</li>";
         if (consequence_info.requires_confirmation) {
           requires_confirmation = true;
         }
       });
       confirmation_markup += "</ul>"
       } else {
         requires_confirmation = data.response[0].requires_confirmation;
         confirmation_markup = "<p><strong>" + data.response[0].description + "</strong></p><p>Are you sure?</p>";
       }

       if (requires_confirmation) {
        $('#transition_confirmation_dialog').html(confirmation_markup);
        $('#transition_confirmation_dialog').dialog('option', 'buttons', {
          'Cancel': function() {$(this).dialog('close');},
          'Confirm': function() {TransitionCommit(id, ct, state);$(this).dialog('close');}
        });
        $('#transition_confirmation_dialog').dialog('open');
       } else {
         TransitionCommit(id, ct, state);
       }
     }
   })
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

function CreateOSTs(fs_id, ost_lun_ids)
{
  $.ajax({type: 'POST', url: "/api/create_osts/", dataType: 'json', data: JSON.stringify({
      "filesystem_id": fs_id,
      "ost_lun_ids": ost_lun_ids
    }), contentType:"application/json; charset=utf-8"})
    .success(function(data, textStatus, jqXHR) 
    {
      if(data.success)
      {
        var response = data.response;    
        //Reload table with latest ost's.
        LoadTargets_EditFS(fs_id);
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
