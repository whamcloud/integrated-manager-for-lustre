

var resource_id = null;

$(document).ready(function() {
  $('#storage_resource_dialog').dialog({autoOpen: false, modal: true, minWidth: 950, maxHeight: 1024});
  $('#alias_save_button').button();
  $('#alias_reset_button').button();
  $('#remove_resource_button').button();
  $('#remove_resource_button').click(remove_resource);

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
  invoke_api_call(api_get, "storage_resource/" + id + "/", {}, 
  success_callback = function(data)
  {
    load_resource(data);
    $('#storage_resource_dialog').dialog('open');
  });
}

function populate_graph(element_id, chart_info, stat_infos) {
  $('#' + element_id).css("width", "300px");
  $('#' + element_id).css("height", "200px");
  var opts = null;

  colors = Highcharts.getOptions().colors

  var type = stat_infos[0].type;
  var unit_name = stat_infos[0].data.unit_name;
  var bin_labels = stat_infos[0].data.bin_labels;
  var enable_legend = stat_infos.length > 1;
  if (type == 'histogram') {
      var series = [];
      $.each(stat_infos, function(i, stat_info) {
        series.push({
          data: stat_info.data.values,
          name: stat_info.label,
          type: 'scatter',
          color: colors[i]
        });
        series.push({
          data: stat_info.data.values,
          name: stat_info.label,
          type: 'areaspline',
          color: colors[i],
          showInLegend: false
        });
      });
      opts = {
          chart: {
              renderTo:element_id,
              type: 'column'
          },
          credits: {enabled: false},
          title: {text: chart_info.title},
          legend: {enabled: enable_legend},
          yAxis: {
              'labels': {enabled: true},
              'title': {text: null},
              'gridLineWidth': 0
          },
          xAxis: {
              categories: bin_labels,
              labels: {style: "font-size: 6pt;", rotation: 90, align: "left", enabled: false},

          },
          series: series,
          plotOptions: {
              'column': {
                  'shadow': false,
                  'pointPadding': 0.0,
                  'groupPadding': 0.0,
              },
              areaspline: {
                marker: {enabled: false},
                lineWidth: 1,
                fillOpacity: 0.25,
                shadow: false
              }
          }
      }
  } else if (type == 'timeseries') {
    var yAxes = [];
    var unit_to_axis = [];
    $.each(stat_infos, function(i, stat_info) {
      if (unit_to_axis[stat_info.data.unit_name] == null) {
        var axis = {
          labels: {enabled: true},
          title: {text: stat_info.data.unit_name},
          min: 0,
          opposite: (yAxes.length % 2)
        }
        yAxes.push(axis);
        unit_to_axis[stat_info.data.unit_name] = yAxes.length - 1;
      }
    });


    var series = [];
    $.each(stat_infos, function(i, stat_info) {
      series.push({
        data: stat_info.data.data_points,
        name: stat_info.label,
        yAxis: unit_to_axis[stat_info.data.unit_name]
      });
    });

    opts = {
        chart: {
            renderTo:element_id,
            type: 'line'
        },
        credits: {enabled: false},
        title: {text: chart_info.title},
        legend: {enabled: enable_legend},
        yAxis: yAxes,
        xAxis: {
            type: 'datetime'
        },
        series: series,
        plotOptions: {
          line: {lineWidth: 1,
                 marker: {enabled: false},
                 shadow: false
                }
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

    $('#remove_resource_button').toggle(resource.scannable)

    var attr_markup = "";
    var rowclass = "odd";
    console.log(resource);
    $.each(resource.attributes, function(i,j) {
      name = j[0]
      attr_info = j[1]
      if (rowclass == "odd") {
        rowclass = "even";
      } else {
          rowclass = "odd";
      }
        attr_markup += "<tr class='" + rowclass + "'><th>" + attr_info.label + ": </th><td>" + attr_info.markup + "</td></tr>";
    }); 
    $('table#storage_attributes').html(attr_markup);

    $('div#storage_alerts').html(alert_indicator_list_markup(resource.id, resource.content_type_id));

    var row = 0;
    var col = 0;
    var row_width = 3;
    var chart_markup = "";
    chart_element_id = new Array();
    $.each(resource.charts, function(i, chart_info) {
      if (col == 0) {
        chart_markup += "<tr>"
      }

      var element_id = "stat_chart_" + i;
      chart_element_id[i] = element_id;
      chart_markup += "<td><div id='" + element_id + "'></div></td>";
      col += 1;
      if (col == row_width) {
        chart_markup += "</tr>"
        col = 0;
      }
    });
    if (col != 0) {
      chart_markup += "</tr>";
    }
    $('table#stats').html(chart_markup);

    $.each(resource.charts, function(i, chart_info) {
      var stat_infos = [];
      $.each(chart_info.series, function(j, stat_name) {
        stat_infos.push(resource.stats[stat_name]);
      });
      populate_graph(chart_element_id[i], chart_info, stat_infos);
    });
}

function remove_resource(ev) {
  invoke_api_call(api_delete, "storage_resource/" + resource_id + "/");
  ev.preventDefault();
}

    function save_alias(new_name) {
        $("a#alias_save_button").hide();
        $("a#alias_reset_button").hide();
        $("img#alias_spinner").show();
        $("input#alias_edit_entry").attr('disabled', 'disabled');

        invoke_api_call(api_put, "storage_resource/" + resource_id + "/", {'alias': new_name}, success_callback = function() {});
        
        $("a#alias_save_button").show()
        $("a#alias_reset_button").show();
        $("img#alias_spinner").hide();
        $("input#alias_edit_entry").removeAttr('disabled');
        
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


