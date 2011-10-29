$(document).ready(function() 
{
// Dialog
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

// Dialog
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


// Dialog
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

// Dialog
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
		SetVisible_TD("ost_container");
        $(this).dialog("close");
      },
      "Cancel": function() { 
        $(this).dialog("close");
      }, 
    }
  });
	
	// Dialog
  $('#newOST').dialog
  ({
    autoOpen: false,
    width: 1100,
    height:470,
    position:"center",
    show: "clip",
    modal: true,
    buttons: 
    {
      "Ok": function() { 
        $(this).dialog("close");
      },
      "Cancel": function() { 
        $(this).dialog("close");
      }, 
    }
  });

// File System Graph
  $('#fs_space').click(function()
  {
    $('#dg_fs_space').dialog('open');
    return false;
  });

// Dialog
  $('#dg_fs_space').dialog
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


// CPU Usage
  $('#cpu_usage').click(function()
  {
    $('#dg_cpu_usage').dialog('open');
      return false;
    });

// Dialog
  $('#dg_cpu_usage').dialog
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

// Dialog
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

  $('#confirm_dialog').dialog
	({
		autoOpen: false,
		width: 300,
		height:150,
		show: "clip",
		modal: true,
		position:"center",
  });
	
});
