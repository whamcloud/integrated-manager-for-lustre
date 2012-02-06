$(document).ready(function() {
  $('#target_dialog').dialog({
    autoOpen: false,
    width: 'auto',
    height: 'auto'
  });
  $('#target_dialog_tabs').tabs();

  $('a.target').live('click', function(event) {
    $.each($(this).attr('class').split(' '), function(i, class_name) {
      if (class_name.indexOf('target_url_') == 0) {
        var target_url = class_name.split('_')[2];
        target_dialog_open(target_url);
      }
    });
    event.preventDefault();
  });
});

target_dialog_link = function(target) {
  return "<a href='#' class='target target_url_" + target.resource_uri + "'>" + object_name_markup(target) + "</a>"
}

target_dialog_open = function(target_url) {
  $('#target_dialog').dialog('open');

  invoke_api_url(api_get, target_url, {}, 
  success_callback = function(target)
  {
    /* TODO: load resource graph by target URI */
    load_resource_graph('target_dialog_devices', target.id);

    $('#target_dialog').dialog('option', 'title', target.human_name);

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
    properties_markup += keyval_row("Name", target.human_name);
    if (target.filesystem_name) {
      properties_markup += keyval_row("Filesystem", target.filesystem_name);
    }
    properties_markup += keyval_row("Primary server", target.primary_server_name);
    properties_markup += keyval_row("Failover server", target.failover_server_name);
    properties_markup += keyval_row("Started on", target.active_host_name);
    properties_markup += keyval_row("Alerts", alert_indicator_large_markup(target.id, target.content_type_id));
    properties_markup += "</table>";
    $('#target_dialog_properties').html(properties_markup);
    if (target.conf_params) {
      $('#target_dialog_tabs').tabs('enable', 2);
      populate_conf_param_table(target.conf_params, "target_config_param_table");
    } else {
      /* Disable the advanced tab */
      $('#target_dialog_tabs').tabs('disable', 2);
    }

    /* FIXME: shoddy way of storing the ID of the currently displayed target */
    $('#config_home_target_id').attr('value', target.id);
  });

}
