//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var Server = Backbone.Model.extend({
  urlRoot: "/api/host/"
});

var ServerDetail = Backbone.View.extend({
  className: 'server_detail',
  template: _.template($('#server_detail_template').html()),
  render: function() {
    var rendered = this.template({'server': this.model.toJSON()});
    $(this.el).find('.ui-dialog-content').html(rendered);

    return this;
  },
  events: {
    "click button.close": "close"
  },
  close: function() {
    this.remove();
    window.history.back();
  }
});