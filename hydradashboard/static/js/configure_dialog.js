$(document).ready(function() {
// Dialog			
	$('#configParam').dialog({
		autoOpen: false,
		width: 400,
		height:480,
		show: "clip",
		modal: true,
		buttons: {
			"Apply": function() { 
				/* $(this).dialog("close"); */
			},
			"Close": function() { 
				$(this).dialog("close"); 
			}, 	
		}
	});
	
	// Dialog Link
	$('#launch_instance_btn-button').click(function(){
		$('#configParam').dialog('open');
		return false;
	});
	
	// Dialog			
	$('#existingMGT').dialog({
		autoOpen: false,
		width: 800,
		height:480,
		show: "clip",
		modal: true,
		buttons: {
			"Ok": function() { 
				$(this).dialog("close");
			},
			"Cancel": function() { 
				/* $(this).dialog("close"); */
			}, 	
		}
	});
	
	// Dialog Link
	$('#btnExistingMGT').click(function(){
		$('#existingMGT').dialog('open');
		return false;
	});
	
		// Dialog			
	$('#newMGT').dialog({
		autoOpen: false,
		width: 800,
		height:480,
		show: "clip",
		modal: true,
		buttons: {
			"Ok": function() { 
				$(this).dialog("close");
			},
			"Cancel": function() { 
				/* $(this).dialog("close"); */
			}, 	
		}
	});
	
	// Dialog Link
	$('#btnNewMGT').click(function(){
		$('#newMGT').dialog('open');
		return false;
	});
	
	// Dialog			
	$('#newMDT').dialog({
		autoOpen: false,
		width: 800,
		height:480,
		show: "clip",
		modal: true,
		buttons: {
			"Ok": function() { 
				$(this).dialog("close");
			},
			"Cancel": function() { 
				/* $(this).dialog("close"); */
			}, 	
		}
	});
	
	// Dialog Link
	$('#btnNewMDT').click(function(){
		$('#newMDT').dialog('open');
		return false;
	});
	
	// Dialog			
	$('#newOST').dialog({
		autoOpen: false,
		width: 800,
		height:480,
		show: "clip",
		modal: true,
		buttons: {
			"Ok": function() { 
				$(this).dialog("close");
			},
			"Cancel": function() { 
				/* $(this).dialog("close"); */
			}, 	
		}
	});
	
	// Dialog Link
	$('#btnNewOST').click(function(){
		$('#newOST').dialog('open');
		return false;
	});
	
	
	// Dialog			
	$('#mgtConfig_newMGT').dialog({
		autoOpen: false,
		width: 800,
		height:480,
		show: "clip",
		modal: true,
		buttons: {
			"Ok": function() { 
				$(this).dialog("close");
			},
			"Cancel": function() { 
				/* $(this).dialog("close"); */
			}, 	
		}
	});
	
	// Dialog Link
	$('#mgtConfig_btnNewMGT').click(function(){
		$('#mgtConfig_newMGT').dialog('open');
		return false;
	});
	
	// File System Graph
	$('#fs_space').click(function(){
		$('#dg_fs_space').dialog('open');
		return false;
	});
	
		// Dialog			
	$('#dg_fs_space').dialog({
		autoOpen: false,
		width: 800,
		height:480,
		show: "clip",
		modal: true,
		buttons: {
			"Close": function() { 
				$(this).dialog("close");
			},
		}
	});
	
	
	// CPU Usage
	$('#cpu_usage').click(function(){
		$('#dg_cpu_usage').dialog('open');
		return false;
	});
	
		// Dialog			
	$('#dg_cpu_usage').dialog({
		autoOpen: false,
		width: 800,
		height:480,
		show: "clip",
		modal: true,
		buttons: {
			"Close": function() { 
				$(this).dialog("close");
			},
		}
	});
	
	// Dialog			
	$('#zoomDialog').dialog({
		autoOpen: false,
		width: 800,
		height:480,
		show: "clip",
		modal: true,
		buttons: {
			"Close": function() { 
				$(this).dialog("close");
			},
		}
	});
});	