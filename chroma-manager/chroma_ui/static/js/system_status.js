//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var SystemStatusView = Backbone.View.extend({
  el: '#toplevel-system_status',
  render: function() {
    var view = this;
    $(view.el).html(_.template($('#system_status_template').html())());
    var supervisor_row_template = _.template($('#system_status_supervisor_process_template').html());

    Api.get("/api/system_status/", {}, function(data) {

      if (data.supervisor == null) {
        $(view.el).find('table.supervisor_processes tbody').html("Unavailable");
      } else {
        _.each(data.supervisor, function(process) {
          var row_markup = supervisor_row_template(process);
          $(view.el).find('table.supervisor_processes tbody').append(row_markup);
        });
      }


    });
  }
});