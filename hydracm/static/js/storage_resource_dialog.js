var resource_id = null;


$(document).ready(function() {
  $('#storage_resource_dialog').dialog({autoOpen: false, modal: true, minWidth: 500, maxHeight: 700});
  $('#alias_save_button').button();
  $('#alias_reset_button').button();

  /* Event for a.storage_resource elements to pop up details dialog */
  $('a.storage_resource').live('click', function() {
    /* Remove leading '#' character */
    id = $(this).attr('href').substring(1)

    popup_resource(id);
  });

  /* If there is an ID of ours in location.hash, pop up */
  var hash_prefix = "#storage_resource_";
  if (window.location.hash.search(hash_prefix) == 0) {
    var resource_id = window.location.hash.substring(hash_prefix.length)
    popup_resource(resource_id);
  }
});

function popup_resource(id) {
  $.get("/api/get_resource/", {'resource_id': id})
   .success(function(data, textStatus, jqXHR) {
      if (data.success) {
        load_resource(data.response);
        console.log('popping up');
        $('#storage_resource_dialog').dialog('open');
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
            alert_markup += "<tr><td><img src='{{STATIC_URL}}images/dialog-error.png'></td><td>" + alrt.alert_message + "</td><td>" + alrt.alert_item + "</td></tr>";
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


