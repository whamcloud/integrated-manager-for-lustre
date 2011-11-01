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

  // Dialog for selecting existing MGTs
  $('#existingMGT').dialog
  ({
    autoOpen: false,
    width: 850,
    height:360,
    show: "clip",
    modal: true,
    position:"center",
    buttons: 
    {
      "Ok": function() { 
    Initialise_MGT(0);
    SetVisible_TD("mdt_container");
        $(this).dialog("close");
      },
      "Cancel": function() { 
    targetid="";
        $(this).dialog("close");
      }, 
    }
  });


 // Dialog for selecting usable luns for creat new MGT
  $('#newMGT').dialog
  ({
    autoOpen: false,
    width: 1100,
    height:460,
    show: "clip",
    modal: true,
    position:"center",
    buttons: 
    {
      "Ok": function() { 
      Initialise_MGT(1);
      SetVisible_TD("mdt_container");
        $(this).dialog("close");
      },
      "Cancel": function() { 
      nodeid="";
        $(this).dialog("close");
      }, 
    }
  });

  // Dialog for selecting usable luns for creat new MDT
  $('#newMDT').dialog
  ({
    autoOpen: false,
    width: 1100,
    height:460,
    show: "clip",
    modal: true,
    position:"center",
    buttons: 
    {
      "Ok": function() { 
      SetNewMDTTableContent('mdt',oNewMDT_RowData);
      //cm-json_table_data.js => call for loading usable luns.
      CreateOST_EditFS();
      SetVisible_TD("ost_container");
        $(this).dialog("close");
      },
      "Cancel": function() { 
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
       var fsname = $('#txtfsnameid').val();       
       var ost_lun_ids = fvc_get_value($('#new_ost_chooser'));

        /* FIXME: hack: using fsname instead of an ID because the edit_fs page loading
         * code doesn't keep the ID anywhere */
        CreateOSTs(fsname, ost_lun_ids);

        $(this).dialog("close");
      },
      "Cancel": function() { 
        $(this).dialog("close");
      }, 
    }
  });
});
