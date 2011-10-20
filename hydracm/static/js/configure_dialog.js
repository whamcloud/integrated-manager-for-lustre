$(document).ready(function() 
{
// Dialog
  $('#configParam').dialog
  ({
    autoOpen: false,
    width: 400,
    height:490,
    show: "clip",
    modal: true,
    position:"top",
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
    width: 800,
    height:360,
    show: "clip",
    modal: true,
    position:"top",
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


// Dialog
  $('#newMGT').dialog
  ({
    autoOpen: false,
    width: 800,
    height:470,
    show: "clip",
    modal: true,
    position:"top",
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



// Dialog
  $('#newMDT').dialog
  ({
    autoOpen: false,
    width: 800,
    height:470,
    show: "clip",
    modal: true,
    position:"top",
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

// Dialog
  $('#newOST').dialog
  ({
    autoOpen: false,
    width: 800,
    height:470,
    position:"top",
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

// Dialog
  $('#mgtConfig_newMGT').dialog
  ({
    autoOpen: false,
    width: 800,
    height:470,
    show: "clip",
    modal: true,
    position:"top",
    buttons: {
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
    position:"top",
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
    position:"top",
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
    position:"top",
    buttons: 
    {
      "Close": function() { 
        $(this).dialog("close");
      },
    }
  });

 //add host dialog - volume config
  $('#addNewHost').dialog
  ({
    autoOpen: false,
    width: 300,
    height:185,
    show: "clip",
    modal: true,
    position:"top",
    buttons: 
    {
      "Continue": function() { 
      AddHost_ServerConfig($('#txtHostName').val(), "addNewHost"); 
      },
    }
  });
});