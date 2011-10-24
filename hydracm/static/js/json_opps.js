function AddHost_ServerConfig(hName, dialog_id)
{
	var oLoadingTable = "<table width='100%' border='0' cellspacing='0' cellpadding='0' align='center' id='loading_tab'><tr><td width='30%'  align='right'><img src='/static/images/loading.gif' width='16' height='16' /></td><td width='90%'  align='left' style='padding-left:5px;'>Checking connectivity</td></tr></table>";
	$('#hostdetails').empty();
	$('#loading_container').html(oLoadingTable);
	var oStatusTable;
	var imgResolve;
	var imgPing;
	var imgAgent;
	
	$.post("/api/testhost/",{"hostname":hName}).success(function(data, textStatus, jqXHR) {
		if(data.success)
		{
			var response = data.response;
			if(response.resolve == false) 
	        {
	            imgResolve="/static/images/dialog-error.png";
	        }
	        if(response.resolve == true)
	        { 
	        	imgResolve="/static/images/dialog_correct.png";
	        }
	        
			if(response.agent == false) 
	        {
	            imgAgent="/static/images/dialog-error.png";
	        }
	        if(response.resolve == true)
	        { 
	        	imgAgent="/static/images/dialog_correct.png";
	        }
			
			if(response.ping == false) 
	        {
	            imgPing="/static/images/dialog-error.png";
	        }
	        if(response.ping == true)
	        { 
	        	imgPing="/static/images/dialog_correct.png";
	        }
			
			$('#loading_tab').empty();
			oStatusTable = "<table width='100%' border='0' cellspacing='0' cellpadding='0' align='center' id='status_tab'><tr><td>Resolve</td><td><img src='" + imgResolve + "' /></td></tr><tr><td>Ping</td><td><img src='" + imgPing + "'/></td></tr><tr><td>Invoke Agent</td><td><img src='" + imgAgent + "'/></td></tr></table>";
			$('#status_container').html(oStatusTable);
			
			$("#" + dialog_id).dialog("option", "buttons", null);
			
			$("#" + dialog_id).dialog({ 
				buttons: { 
					"Close": function() { 
						$(this).dialog("close");
						Add_Host_Table(dialog_id);
					},
					"Add": function() { 
						 Add_Host(response.address, dialog_id);
					}
				} 
			});
        }
	})
	.error(function(event) {
      // Display of appropriate error message
    })
	.complete(function(event) {
	});
}

function Add_Host(host_name, dialog_id)
{
	$.post("/api/addhost/",{"hostname":host_name}).success(function(data, textStatus, jqXHR) {
		if(data.success)
		{
			var response = data.response;		
			var status = "<p>";
			if(response.status=="added")
			{
				$('#status_tab').empty();
				status = status + "Host Added Successfully";
				$("#" + dialog_id).dialog("option", "buttons", null);
				$("#" + dialog_id).dialog({ 
				buttons: { 
					"Close": function() { 
						$(this).dialog("close");
					},
					"Add Another": function() { 
						 Add_Host_Table(dialog_id);
					}
				} 
			});
				$('#server_configuration').dataTable().fnClearTable();
				LoadServerConf_ServerConfig();
			}
			else
			{
				status = status + "Problem occurred while adding host, please try again";
				$("#" + dialog_id).dialog("option", "buttons", null);
				$("#" + dialog_id).dialog({ 
					buttons: { 
						"Close": function() { 
							$(this).dialog("close");
						},
						"Add Another": function() { 
							 Add_Host_Table(dialog_id);
						}
					} 
				});
			}
			status = status + "</p>";
			$('#host_status').html(status);
		}
	})
	.error(function(event) {
      // Display of appropriate error message
    })
	.complete(function(event) {
	});
}

function RemoveConfirmation(host_id)
{
	Confirm("Are you sure you want to remove host?",RemoveHost_ServerConfig(host_id));
}

RemoveHost_ServerConfig = function (host_id)
{
	$.post("/api/removehost/",{"hostid":host_id}).success(function(data, textStatus, jqXHR) {
			if(data.success)
			{
				var response = data.response;		
				if(response.status != "")
				{
					alert("Host " + response.hostid + " Deleted");
					$('#server_configuration').dataTable().fnClearTable();
					LoadServerConf_ServerConfig();
				}
				else
				{
					alert("problem in deleting host");
				}
			}
		})
		.error(function(event) {
		  // Display of appropriate error message
		})
		.complete(function(event) {
		});
}

function Lnet_Operations(host_id, opps)
{
	$.post("/api/setlnetstate/",{"hostid":host_id, "state":opps}).success(function(data, textStatus, jqXHR) {
		if(data.success)
		{
			var response = data.response;		
			if(response.status != "")
			{
				alert("State " + response.hostid + opps + " Changed");
				$('#server_configuration').dataTable().fnClearTable();
				LoadServerConf_ServerConfig();
			}
			else
			{
				alert("problem in deleting host");
			}
		}
	})
	.error(function(event) {
      // Display of appropriate error message
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