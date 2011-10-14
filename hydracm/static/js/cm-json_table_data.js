// JavaScript Document

function LoadFSList_FSList()
{
		$.post("/api/listfilesystems/").success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				var fsName;
				var i=1;
				var action = "<a href='#'> Stop FS</a> | <a href='#'>Config param</a> | <a href='#'>Remove</a>";
				$.each(response, function(resKey, resValue)
                {
	                fsName = "<a href='/hydracm/editfs?fsname=" + resValue.fsname + "'>" +  resValue.fsname + "</a>";
					i++;
					$('#example').dataTable().fnAddData ([
					fsName,
					resValue.mgsname,
					resValue.mdsname,
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
             // Display of appropriate error message
        })
		.complete(function(event) {
		});
	/* table = table + "</tbody>"; */
}


function LoadMGT_EditFS()
{
		var fsname = $('#fs').val();
		var action="--";
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
							action = "<a href='#'>Stop</a>";
						}
						else
						{
							action = "<a href='#'>Start</a>";
						}
						$('#example').dataTable().fnAddData ([
							resValue.targetdevice,												
							resValue.targetname,
							resValue.hostname,
							resValue.failover,
							action
						]);	
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
	var action="--";
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
							action = "<a href='#'>Stop</a>";	 
						}
						else
						{
							action  = "<a href='#'>Start</a>";	 
						}
						$('#mdt').dataTable().fnAddData ([
								resValue.targetdevice,												
								resValue.targetname,
								resValue.hostname,
								resValue.failover,
								"<a href='#'>Stop</a>"
						]);	
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
	var action = "--";
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
							action = "<a href='#'>Stop</a>";	 
						}
						else
						{
							action = "<a href='#'>Start</a>";
						}
						$('#ost').dataTable().fnAddData ([
							resValue.targetdevice,												
							resValue.targetname,
							resValue.hostname,
							resValue.failover,
							action
						]);	
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
	var btnRadio = "<input type='radio' name=existing_mgt' />";
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
								$('#popup-existing-mgt').dataTable().fnAddData ([
									btnRadio,
									resValue.targetmount,												
									resValue.targetname,
									resValue.hostname,
									resValue.failover	  
								]);	
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
    	LoadUsableVolumeList($('#popup-new-mgt'), function(vol_info) {return "<input type='radio' name='mgt'/>"});
}
function CreateNewMDT_EditFS()
{
	$('#popup-new-mdt').dataTable().fnClearTable();
  LoadUsableVolumeList($('#popup-new-mdt'), function(vol_info) {return "<input type='radio' name='mdt'/>"});
}
function CreateOST_EditFS()
{
	$('#popup-new-ost').dataTable().fnClearTable();
  LoadUsableVolumeList($('#popup-new-ost'), function(vol_info) {return "<input type='checkbox' name='" + vol_info.id + "'/>"});
}
function LoadMGTConfiguration_MGTConf()
{
	$('#popup-new-mgt').dataTable().fnClearTable();
	LoadUsableVolumeList($('#popup-new-mgt'), function(vol_info) {return "<input type='checkbox' name='" + vol_info.id + "'/>"});
}


function LoadUsableVolumeList(datatable_container, select_widget_fn)
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
          primarySelect,
		  failoverSelect,
		  resValue.size,										
          resValue.status
        ]);		 
      });
    }
  })
  .error(function(event) {
       // Display of appropriate error message
  })
	.complete(function(event) {
	});
}

function CreateMGT_MGTConf()
{
	var i=1;
	var checkboxCount = 0;
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

        $('#popup-new-ost').dataTable().fnAddData ([
          "<input type='checkbox' id='" + i+ "'/>",
		  resValue.name,
		  primarySelect,
		  failoverSelect,
		  resValue.size,
		  resValue.status
        ]);		 
		$('#'+i).live('click', function() {
						if($(this).attr('checked'))
						{
							checkboxCount++;
							$('#mgtConfig_btnNewMGT').removeAttr('disabled');
						}
						else
						{
							checkboxCount--;
						}
						if(checkboxCount==0)
						{
							$('#mgtConfig_btnNewMGT').attr('disabled', 'disabled');
						}
					});
					i++;
		
      });
    }
  })
  .error(function(event) {
       // Display of appropriate error message
  })
	.complete(function(event) {
	});
}


function LoadMGTConfiguration_MGTConf()
{
		$.post("/api/getvolumesdetails/",{filesystem:""}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				var targetpath="";
				var fsname="";
				var val_targetstatus;
				var val_targetmount;
				var val_hostname;
				var val_failover;
				var updated=0;
				var action ="--";
				
				if(data.response!="")
				{
					$.each(response, function(resKey, resValue)
					{
						if(resValue.targetkind == "MGS")
						{
							if(targetpath!=resValue.targetmount && targetpath!="")
							{
								//fsname = resValue.fsname;	
								if(resValue.targetstatus == "STARTED")
								{
									action = "<a>Stop</a>";		 
								}
								else
								{
									action = "<a>Start</a>";
								}
								$('#mgt_configuration').dataTable().fnAddData ([
									fsname,								
									resValue.targetmount,												
									resValue.hostname,
									resValue.failover,
									action  
								]);	
								fsname="";
								updated=1;
							}
							else
							{
								if (fsname!="")
								{
									fsname = fsname +  "," + resValue.fsname;
								}
								else
								{
									fsname = resValue.fsname;
								}
								val_targetstatus=resValue.targetstatus;
								val_targetmount=resValue.targetmount;
								val_hostname=resValue.hostname;
								val_failover=resValue.failover;
								updated=0;
							}
							targetpath = resValue.targetmount;
						}
						
					});
					if(updated==0)
					{
						if(val_targetstatus == "STARTED")
						{
							action = "<a>Stop</a>";	 
						}
						else
						{
							action = "<a>Start</a>";
						}
						$('#mgt_configuration').dataTable().fnAddData ([
							fsname,								
							val_targetmount,												
							val_hostname,
							val_failover,
							action
						]);	
					}
				}
            }
        })
        .error(function(event)
        {
             // Display of appropriate error message
        })
		.complete(function(event) {
		});
}

function LoadVolumeConf_VolumeConfig()
{
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
             // Display of appropriate error message
        })
		.complete(function(event) {
		});
	}

function LoadServerConf_ServerConfig()
{
	$.post("/api/listservers/",{"filesystem": ""}).success(function(data, textStatus, jqXHR)
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
	$('#fsname').attr('value',fsname);
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
						$('#mdt_file').html(resValue.kbytesused + resValue.mdtfileused);
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