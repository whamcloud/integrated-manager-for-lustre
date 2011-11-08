$(document).ready(function() 
{
  // Dialog for FS advance options
  $('#configParam').dialog
  ({
    autoOpen: false,
    width: 450,
    height:470,
    show: "clip",
    modal: true,
    position:"center",
    buttons: 
    {
      "Apply": function() { 
      /* $(this).dialog("close"); */
      },
      "Close": function() { 
        $(this).dialog("close"); 
      }, 
    }
  });

  // Dialog for selecting usable luns for creat new OST
  $('#new_ost_dialog').dialog
  ({
    autoOpen: false,
    width: 1100,
    maxHeight:470,
    position:"center",
    show: "clip",
    modal: true,
    buttons: 
    {
      "Ok": function() {
       var fs_id = $('#fs_id').val();       
       var ost_lun_ids = fvc_get_value($('#new_ost_chooser'));

        CreateOSTs(fs_id, ost_lun_ids);

        $(this).dialog("close");
      },
      "Cancel": function() { 
        $(this).dialog("close");
      }, 
    }
  });
});
