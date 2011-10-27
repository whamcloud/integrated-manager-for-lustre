
$(document).ready(function() {
  $('#storage_resource_create_dialog').dialog({
    autoOpen: false, modal: true, width: 'auto', maxHeight: 700, title: "Add storage device", resizable: false,
    buttons: {"Cancel": function() {$(this).dialog('close');}, "Add": function() {storage_resource_create_save();}}
  });

  $(document).ajaxComplete(function() {
    $('.storage_resource_create_link').button();
  });
  $('.storage_resource_create_link').live('click', function(ev) {
    storage_resource_create();
    ev.stopPropagation();
  });

  $('#storage_resource_create_classes').change(function() {
    storage_resource_create_load_fields();
  });
});

function storage_resource_create_save()
{
  var selected = $('#storage_resource_create_classes option:selected').val()
  var tokens = selected.split(",")
  var module_name = tokens[0]
  var class_name = tokens[1]

  var attrs = new Object();
  $('#storage_resource_create_fields tr.field input').each(function() {
    var field_name = this.id.split("storage_resource_create_field_")[1];
    var field_value = $(this).attr('value');
    attrs[field_name] = field_value;
    console.log(field_name + " : " + field_value);
  });

  console.log(attrs);

  /* FIXME: this .ajax call should be wrapped up in the same little library that catches errors etc */
  $.ajax({type: 'POST', url: "/api/storage_resource/", dataType: 'json', data: JSON.stringify({'plugin': module_name, 'resource_class': class_name, 'attributes': attrs}), contentType:"application/json; charset=utf-8"})
   .success(function(data, textStatus, jqXHR) {
    $('#storage_resource_create_dialog').dialog('close');
   })

}

function storage_resource_create_load_fields()
{
  var selected = $('#storage_resource_create_classes option:selected').val()
  var tokens = selected.split(",")
  var module_name = tokens[0]
  var class_name = tokens[1]

  $.get("/api/storage_resource_class_fields/", {'plugin': module_name, 'resource_class': class_name})
  .success(function(data, textStatus, jqXHR) {
    if (data.success) {
      $('#storage_resource_create_fields tr.field').remove();
      var row_markup = "";
      $.each(data.response, function(i, field_info) {
        row_markup += "<tr class='field'><th>" + field_info.label + ":</th><td><input type='entry' id='storage_resource_create_field_" + field_info.name + "'></input></td>";
        if (field_info.optional) {
          row_markup += "<td class='field_info'>Optional</td>"
        } else {
          row_markup += "<td class='field_info'></td>"
        }
        row_markup += "</tr>"
      });
      $('#storage_resource_create_fields').append(row_markup);
    $('#storage_resource_create_save').attr('disabled', false);
    }
  });
}

function storage_resource_create() {
  $('#storage_resource_create_save').attr('disabled', true);
  console.log('opening');
  $('#storage_resource_create_dialog').dialog('open');

  $.get("/api/creatable_storage_resource_classes/")
   .success(function(data, textStatus, jqXHR) {
      if (data.success) {
        var option_markup = ""
        $.each(data.response, function(i, class_info) {
          option_markup += "<option value='" + class_info.plugin + "," + class_info.resource_class + "'>" + class_info.plugin + "-" + class_info.resource_class + "</option>"
        });
        $('#storage_resource_create_classes').html(option_markup);
        storage_resource_create_load_fields();
      }
   });
}

function populate_graph(element_id, stat_info) {
  $('#' + element_id).css("width", "400px");
  $('#' + element_id).css("height", "300px");
  var opts = null;
  if (stat_info.type == 'histogram') {
      opts = {
          chart: {
              renderTo:element_id,
              type: 'column'
          },
          credits: {enabled: false},
          title: {text: stat_info.name},
          legend: {enabled: false},
          yAxis: {
              'labels': {enabled: true},
              'title': {text: null},
              'gridLineWidth': 0
          },
          xAxis: {
              categories: stat_info.data.bin_labels,
              labels: {style: "font-size: 6pt;", rotation: 60, align: "left"}
          },
          series: [{
              'data': stat_info.data.values,
              'name': 'Samples'
          }],
          plotOptions: {
              'column': {
                  'shadow': false,
                  'pointPadding': 0.0,
                  'groupPadding': 0.0,
              }
          }
      }
  } else if (stat_info.type == 'timeseries') {
      opts = {
          chart: {
              renderTo:element_id,
              type: 'line'
          },
          credits: {enabled: false},
          title: {text: stat_info.name},
          legend: {enabled: false},
          yAxis: {
              labels: {enabled: true},
              title: {text: stat_info.data.unit_name},
              min: 0
          },
          xAxis: {
              type: 'datetime'
          },
          series: [{
              data: stat_info.data.data_points,
              name: stat_info.name
          }],
          plotOptions: {
          }
      }
  }
  chart = new Highcharts.Chart(opts);
}

function load_resource(resource) {
    resource_id = resource.id
    window.location.hash = "storage_resource_" + resource_id
    $('#storage_resource_dialog').dialog("option", "title", resource.class_name)

    if (resource.alias) {
        $("input#alias_edit_entry").attr('value', resource.alias);
    } else {
        $("input#alias_edit_entry").attr('value', resource.default_alias);
    }
        $("input#alias_default_entry").attr('value', resource.default_alias);

        var attr_markup = "";
        var rowclass = "odd";
        $.each(resource.attributes, function(k,v) {
          if (rowclass == "odd") {
            rowclass = "even";
          } else {
              rowclass = "odd";
          }
            attr_markup += "<tr class='" + rowclass + "'><th>" + k + ": </th><td>" + v.markup + "</td></tr>";
        }); 
        $('table#attributes').html(attr_markup);

        var alert_markup = "";
        $.each(resource.alerts, function(i, alrt) {
            console.log(i);
            console.log(alrt);
            alert_markup += "<tr><td><img src='/static/images/dialog-error.png'></td><td>" + alrt.alert_message + "</td><td>" + alrt.alert_item + "</td></tr>";
        }); 
        $('table#alerts').html(alert_markup);

        var stats_markup = "";
        stat_graph_element_id = new Array();
        $.each(resource.stats, function(stat_name, stat_info) {
                var element_id = "stat_graph_" + stat_name;
                stat_graph_element_id[stat_name] = element_id;
                stats_markup += "<li><div id='" + element_id + "'></div></li>";
        });
        $('ul#stats').html(stats_markup);

        $.each(resource.stats, function(stat_name, stat_info) {
            populate_graph(stat_graph_element_id[stat_name], stat_info);
        });
    }

    function save_alias(new_name) {
        $("a#alias_save_button").hide();
        $("a#alias_reset_button").hide();
        $("img#alias_spinner").show();
        $("input#alias_edit_entry").attr('disabled', 'disabled');

        $.post("/api/set_resource_alias/", {'resource_id': resource_id,'alias': new_name})
            .success(function(){console.log('success');})
            .error(function(){console.log("Error posting new alias");})
            .complete(function(){
              console.log('complete');
              $("a#alias_save_button").show()
              $("a#alias_reset_button").show();
              $("img#alias_spinner").hide();
              $("input#alias_edit_entry").removeAttr('disabled');
            })
    }
    $(document).ready(function() {
        $("a#alias_reset_button").click(function() {
            var reset_val = $("input#alias_default_entry").attr('value');
            $("input#alias_edit_entry").attr('value', reset_val);
            save_alias("");

        });
        $("a#alias_save_button").click(function() {
            var new_name = $("input#alias_edit_entry").attr('value');
            save_alias(new_name);
        })
    });


