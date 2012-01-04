$(document).ready(function() {
  $('#target_dialog').dialog({
    autoOpen: false,
    width: 'auto',
    height: 'auto'
  });
  $('#target_dialog_tabs').tabs();

  $('a.target').live('click', function(event) {
    $.each($(this).attr('class').split(' '), function(i, class_name) {
      if (class_name.indexOf('target_id_') == 0) {
        var target_id = class_name.split('_')[2];
        target_dialog_open(target_id);
      }
    });
    event.preventDefault();
  });
});

target_dialog_open = function(target_id) {
  $('#target_dialog').dialog('open');

  load_resource_graph('target_dialog_devices', target_id);
  
  invoke_api_call(api_post, "target/", {id: target_id}, 
  success_callback = function(data)
  {
    var target_info = data.response;
    console.log(target_info);
    $('#target_dialog').dialog('option', 'title', target_info.human_name);

    var row_counter = 0;
    var keyval_row = function(k,v) {
      row_counter += 1;
      var row_class;
      if (row_counter % 2 == 0) {
        row_class = 'even';
      } else {
        row_class = 'odd';
      }

      return "<tr class='" + row_class + "'><th>" + k + ":</th><td>" + v + "</td></tr>"
    }

    var properties_markup = "";
    properties_markup += "<table>";
    properties_markup += keyval_row("Name", target_info.human_name);
    if (target_info.filesystem_name) {
      properties_markup += keyval_row("Filesystem", target_info.filesystem_name);
    }
    properties_markup += keyval_row("Primary server", target_info.primary_server_name);
    properties_markup += keyval_row("Failover server", target_info.failover_server_name);
    properties_markup += keyval_row("Started on", target_info.active_host_name);
    properties_markup += keyval_row("Alerts", alert_indicator_large_markup(target_info.id, target_info.content_type_id));
    properties_markup += "</table>";
    $('#target_dialog_properties').html(properties_markup);
  });

  $('#config_home_target_id').attr('value',target_id);
  //load Config param in target dialog box.
  GetConfigurationParam(target_id,"", "target_config_param_table");
}
