// JavaScript Document

function loadData()
{
		$.post("/api/listfilesystems/").success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				var fsName;
				var i=1;
				$.each(response, function(resKey, resValue)
                {
	                fsName = "<a href='/hydracm/newfstab?fsname=" + resValue.fsname + "'>" +  resValue.fsname + "</a>";
					i++;
					$('#example').dataTable().fnAddData ([
					fsName,
					resValue.mgsname,
					resValue.mdsname,
					resValue.noofoss,
					resValue.noofost,
					resValue.kbytesused,
					resValue.kbytesfree,
					"Stop FS | Config param | Remove"				  
					]);		 
                });
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
		.complete(function(event) {
		});
	/* table = table + "</tbody>"; */
}


function LoadMGT_EditFS()
{
		var fsname = $('#fs').val();
		$.post("/api/getvolumesdetails/",{filesystem:fsname}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				$.each(response, function(resKey, resValue)
                {
					if(resValue.targetkind == "MGS")
					{
						if(resValue.targetstatus == "STARTED")
						{
							$('#example').dataTable().fnAddData ([
							resValue.targetmount,												
							resValue.targetname,
							resValue.targetkind,
							resValue.hostname,
							resValue.failover,
							"<a>Stop</a>"		  
							]);		 
						}
						else
						{
							$('#example').dataTable().fnAddData ([
							resValue.targetmount,												
							resValue.targetname,
							resValue.targetkind,
							resValue.hostname,
							resValue.failover,
							"<a>Start</a>"		  
							]);	
						}
					}
                });
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
		.complete(function(event) {
		});
}

function LoadMDT_EditFS()
{
	var fsname = $('#fs').val();
	$.post("/api/getvolumesdetails/",{filesystem:fsname}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				$.each(response, function(resKey, resValue)
                {
					if(resValue.targetkind == "MDT")
					{
						if(resValue.targetstatus == "STARTED")
						{
							$('#mdt').dataTable().fnAddData ([
								resValue.targetdevice,												
								resValue.targetname,
								resValue.targetkind,
								resValue.hostname,
								resValue.failover,
								"<a>Stop</a>"		  
							]);		 
						}
						else
						{
							$('#mdt').dataTable().fnAddData ([
								resValue.targetdevice,												
								resValue.targetname,
								resValue.targetkind,
								resValue.hostname,
								resValue.failover,
								"<a>Start</a>"		  
							]);		 
						}
					}
                });
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
		.complete(function(event) {
		});
}


function LoadOST_EditFS()
{
	var fsname = $('#fs').val();
		$.post("/api/getvolumesdetails/",{filesystem:fsname}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				$.each(response, function(resKey, resValue)
                {
					if(resValue.targetkind == "OST")
					{
						if(resValue.targetstatus == "STARTED")
						{
							$('#ost').dataTable().fnAddData ([
							resValue.targetmount,												
							resValue.targetname,
							resValue.targetkind,
							resValue.hostname,
							resValue.failover,
							"<a>Stop</a>"		  
							]);		 
						}
						else
						{
							$('#ost').dataTable().fnAddData ([
							resValue.targetmount,												
							resValue.targetname,
							resValue.targetkind,
							resValue.hostname,
							resValue.failover,
							"<a>Start</a>"		  
							]);	
						}
					}
                });
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
		.complete(function(event) {
		});

}


function LoadExistingMGT_EditFS()
{
	$('#popup-existing-mgt').dataTable().fnClearTable();
		$.post("/api/getvolumesdetails/",{filesystem:""}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				var updatedTargetMnt="";
				$.each(response, function(resKey, resValue)
                {
						if(resValue.targetkind == "MGS")
						{
							if(updatedTargetMnt != resValue.targetmount)
							{
								if(resValue.targetstatus == "STARTED")
								{
									$('#popup-existing-mgt').dataTable().fnAddData ([
									resValue.targetmount,												
									resValue.targetname,
									resValue.targetkind,
									resValue.hostname,
									resValue.failover,
									"<a>Stop</a>"		  
									]);		 
								}
								else
								{
									$('#popup-existing-mgt').dataTable().fnAddData ([
									resValue.targetmount,												
									resValue.targetname,
									resValue.targetkind,
									resValue.hostname,
									resValue.failover,
									"<a>Start</a>"		  
									]);	
								}
						}
						updatedTargetMnt = resValue.targetmount;
					}	
                });
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
		.complete(function(event) {
		});
}

function CreateNewMGT_EditFS()
{
		$('#popup-new-mgt').dataTable().fnClearTable();
    loadUsableVolumeList($('#popup-new-mgt'), function(vol_info) {return "<input type='radio' name='mgt'/>"});
}


function CreateNewMDT_EditFS()
{
	$('#popup-new-mdt').dataTable().fnClearTable();
  loadUsableVolumeList($('#popup-new-mdt'), function(vol_info) {return "<input type='radio' name='mdt'/>"});
}

function CreateOST_EditFS()
{
	$('#popup-new-ost').dataTable().fnClearTable();
  loadUsableVolumeList($('#popup-new-ost'), function(vol_info) {return "<input type='checkbox' name='" + vol_info.id + "'/>"});
}


function LoadMGTConfiguration_MGTConf()
{
		$.post("/api/getvolumesdetails/",{filesystem:""}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				$.each(response, function(resKey, resValue)
                {
					if(resValue.targetkind == "MGS")
					{
						if(resValue.targetstatus == "STARTED")
						{
							$('#mgt_configuration').dataTable().fnAddData ([
							resValue.targetmount,												
							resValue.targetname,
							resValue.hostname,
							resValue.failover,
							"<a>Stop</a>"		  
							]);		 
						}
						else
						{
							$('#mgt_configuration').dataTable().fnAddData ([
							resValue.targetmount,												
							resValue.targetname,
							resValue.hostname,
							resValue.failover,
							"<a>Start</a>"		  
							]);		 
						}
					}
                });
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
		.complete(function(event) {
		});
}

function loadUsableVolumeList(datatable_container, select_widget_fn)
{
  $.get("/api/get_luns/", {'category': 'usable'}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      $.each(data.response, function(resKey, volume_info)
      {
        var primaryHostname = "---"
        var failoverHostname = "---"
        $.each(volume_info.available_hosts, function(host_id, host_info) {
          if (host_info.primary) {
            primaryHostname = host_info.label
          } else if (host_info.use) {
            failoverHostname = host_info.label
          }
        });

        datatable_container.dataTable().fnAddData ([
          select_widget_fn(volume_info),
          volume_info.name,											
          volume_info.size,		  
          volume_info.kind,											
          volume_info.status,
          primaryHostname,
          failoverHostname,
        ]);		 
      });
    }
  })
  .error(function(event)
  {
       // Display of appropriate error message
  })
}

function loadUnusedVolumeList()
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
        $.each(resValue.available_hosts, function(host_id, host_info) {
          host_count += 1;
        });
        if (host_count == 0) {
          primarySelect = blank_select
          failoverSelect = blank_select
        } else if (host_count == 1) {
          $.each(resValue.available_hosts, function(host_id, host_info) {
            primarySelect = "<select disabled='disabled'><option value='" + host_id + "'>" + host_info.label + "</option></select>";
          });
          failoverSelect = blank_select
        } else {
          primarySelect = "<select>";
          failoverSelect = "<select>";
          primarySelect += blank_option
          failoverSelect += blank_option
          $.each(resValue.available_hosts, function(host_id, host_info)
          {
            if (host_info.primary) {
              primarySelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
            } else if (host_info.use) {
              primarySelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
            } else {
              primarySelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
            }
          });
          failoverSelect += "</select>";
          primarySelect += "</select>";
        }

        $('#volume_configuration').dataTable().fnAddData ([
          resValue.name,											
          resValue.size,		  
          resValue.kind,											
          resValue.status,
          primarySelect,
          failoverSelect,
        ]);		 
      });
    }
  })
  .error(function(event)
  {
       // Display of appropriate error message
  })
}

function loadServerConfiguration()
{
	$.post("/api/listservers/",{"hostid": ""}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				var lnet_status_mesg;
				$.each(response, function(resKey, resValue)
                {
					if(resValue.lnet_status == "OK")
					{
						lnet_status_mesg = "<a href='#'>Stop Lnet</a> | <a href='#'>Remove</a> | <a href='#'>Unload Lnet</a> | <a href='#'>Configuration</a>";
					}
					else
					{
						lnet_status_mesg = "<a href='#'>Start Lnet</a> | <a href='#'>Remove</a> | <a href='#'>Unload Lnet</a> | <a href='#'>Configuration</a>";
					}
					$('#server_configuration').dataTable().fnAddData ([
						resValue.host_address,											
						resValue.failnode,
						resValue.lnet_status,
						lnet_status_mesg
					]);		 
				});
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
		.complete(function(event) {
		});
}

function LoadFSData_EditFS()
{
	var fsname = $('#fs').val();
	if(fsname!="none")
	{
		$.post("/api/getfilesystem/",{"filesystem":fsname}).success(function(data, textStatus, jqXHR)
		{
				if(data.success)
				{
					var response = data.response;
					var lnet_status_mesg;
					$.each(response, function(resKey, resValue)
					{
						$('#total_capacity').html(resValue.kbytesused + resValue.kbytesfree);
						$('#inodes').html(resValue.kbytesused + resValue.kbytesfree);
						$('#total_oss').html(resValue.noofoss);
						$('#total_ost').html(resValue.noofost);
					});
				}
			})
			.error(function(event)
			{
				 // Display of appropriate error message
			})
			.complete(function(event) {
			});
	}
}
