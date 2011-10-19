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