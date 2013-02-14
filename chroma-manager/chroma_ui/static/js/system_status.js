//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var SystemStatusView = Backbone.View.extend({
  el: '#toplevel-system_status',
  update_period: 5000,
  render: function() {
    var view = this;
    $(view.el).html(_.template($('#system_status_template').html())());
    Api.get("/api/system_status/", {}, function(data) {
      var table = $(view.el).find('table.supervisor_processes');
      if (data.supervisor == null) {
        table.html("Unavailable");
      } else {
        table.dataTable({
          bJQueryUI: true,
          aaSorting: [[0, 'asc']],
          aoColumns: [
            {
              sTitle: 'Name',
              mDataProp: 'name'
            },
            {
              sTitle: 'Description',
              mDataProp: 'description'
            },
            {
              sTitle: 'State',
              mDataProp: 'statename'
            }
          ],
          aaData: data.supervisor
        });
      }

      var sorting = {
        'pg_stat_user_tables': [['n_tup_ins', 'desc']],
        'pg_statio_user_tables': [['heap_blks_hit', 'desc']]
      };

      function populate_table(table_name, table, table_data) {
        var columns = [];
        _.each(table_data.columns, function(column) {
          columns.push({'sTitle': column})
        });

        var idx_sorting = [];
        if (sorting[table_name]) {
          _.each(sorting[table_name], function(sort) {
            var idx;
            _.each(columns, function(col, i) {
              if (col['sTitle'] == sort[0]) {
                idx = i;
              }
            });
            idx_sorting.push([idx, sort[1]])
          });
        }

        table.dataTable({
          bJQueryUI: true,
          iDisplayLength: 20,
          aaData: table_data.rows,
          aoColumns: columns,
          aaSorting: idx_sorting
        });
      }

      var rabbitmq_columns = [
        {
          sTitle: 'Name',
          mDataProp: 'name'
        },
        {
          sTitle: 'Durable',
          mDataProp: 'durable'
        },
        {
          sTitle: 'Memory',
          mDataProp: 'memory'
        },
        {
          sTitle: 'Queue length',
          mDataProp: 'messages'
        },
        {
          sTitle: 'Publish rate',
          mDataProp: 'message_stats_publish_details_rate'
        },
        {
          sTitle: 'Ack rate',
          mDataProp: 'message_stats_ack_details_rate'
        }
      ];

      var rabbitmq_table = $('table.rabbitmq_queues');
      if (data.rabbitmq) {
        _.each(data.rabbitmq.queues, function(q) {
          q['message_stats_publish_details_rate'] = q['message_stats_publish_details_rate'].toFixed(2);
          q['message_stats_ack_details_rate'] = q['message_stats_ack_details_rate'].toFixed(2);
        });
        rabbitmq_table.dataTable({
          bJQueryUI: true,
          iDisplayLength: 10,
          aaData: data.rabbitmq.queues,
          aoColumns: rabbitmq_columns,
          aaSorting: [[3, 'desc'], [4, 'desc'], [5, 'desc']],
          bLengthChange: false,
          bSearchable: false
        });
      } else {
        rabbitmq_table.html("Unavailable")
      }

      populate_table('pg_stat_activity', $(view.el).find('table.pg_stat_activity'), data.postgres.pg_stat_activity);

      _.each(data.postgres.table_stats, function(table_stats, stats_table_name) {
        var header_markup = "<h4>" + stats_table_name + "</h4>";
        var table_markup = "<table class='" + stats_table_name + " display tight_lines'><thead><tr></tr></thead><tbody></tbody></table>";
        $(view.el).find('.postgres_table_stats').append(header_markup);
        $(view.el).find('.postgres_table_stats').append(table_markup);
        populate_table(stats_table_name, $(view.el).find('table.' + stats_table_name), table_stats);
      });

      setTimeout(function() {view.update(data);}, view.update_period);
    });
  },
  update: function(prev_data) {
    var view = this;

    Api.get("/api/system_status/", {}, function(data) {

      if (data.supervisor) {
        var supervisor_table = $(view.el).find('table.supervisor_processes');
        supervisor_table.dataTable().fnClearTable();
        supervisor_table.dataTable().fnAddData(data.supervisor);
      }

      if (data.rabbitmq) {
        _.each(data.rabbitmq.queues, function(q) {
          q['message_stats_publish_details_rate'] = q['message_stats_publish_details_rate'].toFixed(2);
          q['message_stats_ack_details_rate'] = q['message_stats_ack_details_rate'].toFixed(2);
        });
        var rabbitmq_table = $('table.rabbitmq_queues');
        rabbitmq_table.dataTable().fnClearTable();
        rabbitmq_table.dataTable().fnAddData(data.rabbitmq.queues);
      }

      var rate_data = {};
      _.each(data.postgres.table_stats, function(table_stats, stats_table_name) {
        var old_stats = prev_data.postgres.table_stats[stats_table_name];
        rate_data[stats_table_name] = []
        _.each(table_stats.rows, function(row, i) {
          rate_data[stats_table_name][i] = [];
          _.each(row, function(cell, j) {
            var old_data = old_stats.rows[i][j];
            if (typeof(old_data) === 'number') {
              rate_data[stats_table_name][i][j] = (cell - old_data) / (view.update_period / 1000.0);
            } else{
              rate_data[stats_table_name][i][j] = cell;
            }
          });
        });
      });
      _.each(rate_data, function(table_stats, stats_table_name) {
        var table = $(view.el).find('table.' + stats_table_name);
        table.dataTable().fnClearTable();
        table.dataTable().fnAddData(table_stats);
      });

      setTimeout(function(){view.update(data)}, view.update_period);
    }, undefined, false);
  }
});