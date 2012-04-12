
var Target = Backbone.Model.extend({
  urlRoot: "/api/target/"
});

var TargetDetail = Backbone.View.extend({
  className: 'target_detail',
  template: _.template($('#target_detail_template').html()),
  render: function() {
    var rendered = this.template({target: this.model.toJSON()});
    $(this.el).find('.ui-dialog-content').html(rendered);
    $(this.el).find('.tabs').tabs();

    load_resource_graph($(this.el).find(".resource_graph_canvas"), this.model.get('id'));

    var conf_params = this.model.get('conf_params');
    if (conf_params != null) {
      $(this.el).find(".conf_param_table").dataTable( {
        "iDisplayLength":30,
        "bProcessing": true,
        "bJQueryUI": true,
        "bPaginate" : false,
        "bSort": false,
        "bFilter" : false,
        "bAutoWidth":false,
        "aoColumns": [
          { "sClass": 'txtleft' },
          { "sClass": 'txtcenter' },
          { "bVisible": false }
        ]
      });

      populate_conf_param_table(conf_params, $(this.el).find(".conf_param_table"));
    }

    return this;
  },
  conf_param_apply: function() {
    apply_config_params(
      this.model.get('resource_uri'),
      $(this.el).find(".conf_param_table").dataTable());
  },
  conf_param_reset: function() {
    reset_config_params($(this.el).find(".conf_param_table").dataTable());
  },
  events: {
    "click .conf_param_apply": "conf_param_apply",
    "click .conf_param_reset": "conf_param_reset",
    "click button.close": "close"
  },
  close: function() {
    this.remove();
    window.history.back();
  }
});