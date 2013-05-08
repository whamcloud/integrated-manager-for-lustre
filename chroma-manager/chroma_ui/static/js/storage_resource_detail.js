//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


var StorageResource = Backbone.Model.extend({
  urlRoot: "/api/storage_resource/"
});

var StorageResourceDetail = Backbone.View.extend({
  className: 'storage_resource_detail',
  template: _.template($('#storage_resource_detail_template').html()),
  render: function() {
    var view = this;

    var rendered = view.template(view.model.toJSON());
    $(view.el).find('.ui-dialog-content').html(rendered);

    $(view.el).find('.alias_save_button').button();
    $(view.el).find('.alias_reset_button').button();
    $(view.el).find('.remove').button();
    $(view.el).find('.storage_alerts').html(LiveObject.alertList(view.model.toJSON()));
    $(view.el).find('a.del').button();

    var col = 0;
    var row_width = 3;
    var chart_markup = "";
    var chart_element_id = new Array();
    $.each(view.model.get('charts'), function(i, chart_info) {
      if (col == 0) {
        chart_markup += "<tr>"
      }

      var element_id = "stat_chart_" + i;
      chart_element_id[i] = element_id;
      chart_markup += "<td><div class='relative'><div id='" + element_id + "'></div></div></td>";
      col += 1;
      if (col == row_width) {
        chart_markup += "</tr>";
        col = 0;
      }
    });
    if (col != 0) {
      chart_markup += "</tr>";
    }
    $(view.el).find('table.storage_statistics').html(chart_markup);

    var chart_manager = ChartManager({chart_group: 'storage_resource_detail'});
    var stats = view.model.get('stats');
    var resource_uri = view.model.get('resource_uri');

    $.each(view.model.get('charts'), function(i, chart_info) {
      $('#' + chart_element_id[i]).css("width", "300px");
      $('#' + chart_element_id[i]).css("height", "200px");

      var stat_infos = [];
      var is_histogram = false;
      var missing_stats = false;
      $.each(chart_info.series, function(j, stat_name) {
        var stat_info = stats[stat_name];
        if (!stat_info) {
          missing_stats = true;
          return;
        }

        stat_infos.push(stat_info);
        if (stat_info.type == 'histogram') {
          is_histogram = true;
        }
      });

      if (missing_stats) {
        // One or more series was unavailable, give up.
        return;
      }

      var enable_legend = stat_infos.length > 1;

      if (is_histogram) {
        // For histogram charts, we generate our own static graph
        view.render_histogram(chart_element_id[i], chart_info, stat_infos);
      } else {
        // For time series charts, we use ChartManager
        var yAxes = [];
        var unit_to_axis = [];
        var series = [];
        var metrics = [];
        $.each(stat_infos, function(i, stat_info) {
          series.push({'name': stat_info.label});
          if (unit_to_axis[stat_info.unit_name] == null) {
            var axis = {
              labels: {enabled: true},
              title: {text: stat_info.unit_name},
              min: 0,
              opposite: (yAxes.length % 2)
            };
            yAxes.push(axis);
            unit_to_axis[stat_info.unit_name] = yAxes.length - 1;
          }
          metrics.push(stat_info.name)
        });
        chart_manager.add_chart(chart_element_id[i], 'storage_resource_detail',
          {
            url: resource_uri + "metric/",
            metrics: metrics,
            chart_config: {
              chart: {
                type: 'line',
                renderTo: chart_element_id[i]
              },
              title: {text: chart_info.title},
              legend: {enabled: enable_legend},
              yAxis: yAxes,
              xAxis: {
                type: 'datetime'
              },
              series: series
            }
          });
      }
    });
    chart_manager.init();

    return view;
  },
  events: {
    "click button.del": "del",
    "click button.save_alias": "save_alias",
    "click button.reset_alias": "reset_alias"
  },
  del: function() {
    var view = this;
    this.model.destroy({success: function(){
      $(view.el).remove();
      window.history.back();
    }});
  },
  reset_alias: function() {
    $(this.el).find(".alias").attr('value', this.model.get('default_alias'));
  },
  save_alias: function() {
    var save_button = $(this.el).find('a.save_alias');
    var reset_button = $(this.el).find('a.save_alias');
    save_button.hide();
    reset_button.hide();
    ValidatedForm.clear_errors($(this.el));
    var alias_entry = $(this.el).find('.alias');
    alias_entry.attr('disabled', 'disabled');

    var new_name = alias_entry.attr('value');
    if (new_name == this.model.get('default_alias')) {
      new_name = null;
    }

    this.model.save({'alias': new_name}, {
      success: function () {
        save_button.show();
        reset_button.show();
        alias_entry.removeAttr('disabled');
      },
      error: function (model, responseText){
        var errors = JSON.parse(responseText);
        if (errors.alias) {
          _.each(errors.alias, function(message) {
            ValidatedForm.add_error(alias_entry, message);
          });
        }

        save_button.show();
        reset_button.show();
        alias_entry.removeAttr('disabled');
      }
    });
  },
  render_histogram: function(element_id, chart_info, stat_infos) {
    $('#' + element_id).css("width", "300px");
    $('#' + element_id).css("height", "200px");

    var colors = Highcharts.getOptions().colors;

    var bin_labels = stat_infos[0].data.bin_labels;
    var enable_legend = stat_infos.length > 1;
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
    var opts = {
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
        labels: {style: "font-size: 6pt;", rotation: 90, align: "left", enabled: false}
      },
      series: series,
      plotOptions: {
        'column': {
          'shadow': false,
          'pointPadding': 0.0,
          'groupPadding': 0.0
        },
        areaspline: {
          marker: {enabled: false},
          lineWidth: 1,
          fillOpacity: 0.25,
          shadow: false
        }
      }
    };

    new Highcharts.Chart(opts);
  }
});