function fslist_resize(iframe)
{
	$("#" + iframe).height($("#" + iframe).contents().find("#example").height() + 200 + "px");
}

function MGTConfig_resize(iframe)
{
	var height=0;
	height = ($("#" + iframe).contents().find("#mgt_configuration").height()) + ($("#" + iframe).contents().find("#popup-new-ost").height());
	height = height + 200;
	
	$("#" + iframe).height(height + "px");
}

$(document).ready(function() {	
	$('#cancel_editfs').click(function() {
	 	$('#lusterFS_content').empty();
		$('#lusterFS_content').load('/hydracm/fstab');
	});
});

function LoadEditFSScreen(fs_name)
{
	$('#lusterFS_content').empty();
		LoadMGT_EditFS(fs_name); 
		LoadMDT_EditFS(fs_name); 
		LoadOST_EditFS(fs_name); 
	$('#lusterFS_content').load('/hydracm/editfs?fsname=' + fs_name);
}
