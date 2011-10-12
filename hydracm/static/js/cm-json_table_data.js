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
		$.post("/api/getdevices/",{"hostid": ""}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				var failoverSelect;
				$.each(response, function(resKey, resValue)
                {
					if(resKey == 0)
					{
						failoverSelect = "<select>";
						$.each(resValue.failover, function(resFailoverKey, resFailoverValue)
						{
							failoverSelect = failoverSelect + "<option value='volvo'>" + resFailoverValue.failoverhost + "</option>";
						});
						failoverSelect = failoverSelect + "</select>";
					}
					$('#popup-new-mgt').dataTable().fnAddData ([
						"<input type='radio' name='mgt'/>",
						resValue.devicepath,											
						"<select><option value='volvo'>" + resValue.host + "</option></select>",
						resValue.host,
						failoverSelect,
						resValue.devicecapacity,
						resValue.isprimary,
						resValue.lun,
						resValue.lunname
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


function CreateNewMDT_EditFS()
{
	$('#popup-new-mdt').dataTable().fnClearTable();
	$.post("/api/getdevices/",{"hostid": ""}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				var failoverSelect;
				$.each(response, function(resKey, resValue)
                {
					if(resKey == 0)
					{
						failoverSelect = "<select>";
						$.each(resValue.failover, function(resFailoverKey, resFailoverValue)
						{
							failoverSelect = failoverSelect + "<option value='volvo'>" + resFailoverValue.failoverhost + "</option>";
						});
						failoverSelect = failoverSelect + "</select>";
					}
					$('#popup-new-mdt').dataTable().fnAddData ([
						"<input type='radio' name='mdt'/>",
						resValue.devicepath,											
						resValue.host,
						failoverSelect,
						resValue.devicecapacity,
						resValue.isprimary,
						resValue.lun,
						resValue.lunname
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

function CreateOST_EditFS()
{
		$('#popup-new-ost').dataTable().fnClearTable();
		$.post("/api/getdevices/",{"hostid": ""}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				var failoverSelect;
				$.each(response, function(resKey, resValue)
                {
					if(resKey == 0)
					{
						failoverSelect = "<select>";
						$.each(resValue.failover, function(resFailoverKey, resFailoverValue)
						{
							failoverSelect = failoverSelect + "<option value='volvo'>" + resFailoverValue.failoverhost + "</option>";
						});
						failoverSelect = failoverSelect + "</select>";
					}
					$('#popup-new-ost').dataTable().fnAddData ([
						"<input type='checkbox' name='" + resValue.devicepath + "'/>",
						resValue.devicepath,
						resValue.host,
						failoverSelect,
						resValue.devicecapacity,
						resValue.isprimary,
						resValue.lun,
						resValue.lunname
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

function loadVolumeConfiguration()
{
		$.post("/api/getdevices/",{"hostid": ""}).success(function(data, textStatus, jqXHR)
        {
            if(data.success)
            {
                var response = data.response;
				var failoverSelect;
				$.each(response, function(resKey, resValue)
                {
					if(resKey == 0)
					{
						failoverSelect = "<select>";
						$.each(resValue.failover, function(resFailoverKey, resFailoverValue)
						{
							failoverSelect = failoverSelect + "<option value='volvo'>" + resFailoverValue.failoverhost + "</option>";
						});
						failoverSelect = failoverSelect + "</select>";
					}
					$('#volume_configuration').dataTable().fnAddData ([
						resValue.devicepath,											
						"<select><option value='volvo'>" +resValue.host + "</option></select>",
						failoverSelect,
						resValue.devicestatus,
						resValue.devicecapacity		  
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