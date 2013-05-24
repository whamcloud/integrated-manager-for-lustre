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


var Target = Backbone.Model.extend({
  urlRoot: "/api/target/"
});

var TargetDetail = Backbone.View.extend({
  className: 'target_detail',
  template: _.template($('#target_detail_template').html()),
  render: function () {
    var cleanModel = this.model.toJSON();
    var rendered = this.template({target: cleanModel});
    var view = this;
    $(this.el).find('.ui-dialog-content').html(rendered);
    $(this.el).find('.tabs').tabs({'show': function(event, ui) {view.tab_select(event, ui)}});

    var generateCommandDropdown = angular.element('html').injector().get('generateCommandDropdown');
    generateCommandDropdown.generateDropdown($(this.el).find('div[command-dropdown]'), cleanModel);

    var conf_params = this.model.get('conf_params');
    if (conf_params != null && !this.model.get('immutable_state')) {
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
      ContextualHelp.load_snippets('#target_dialog_config_param_tab');
    }

    return this;
  },
  conf_param_apply: function() {
    apply_config_params(
      this.model.toJSON(),
      $(this.el).find(".conf_param_table").dataTable());
  },
  conf_param_reset: function () {
    var dataTable = $(this.el).find('.conf_param_table').dataTable();

    window.reset_config_params(dataTable);
    this.conf_param_apply(dataTable);
  },
  conf_param_cancel: function () {
    window.cancel_config_params($(this.el).find('.conf_param_table').dataTable());
  },
  tab_select: function(event, ui) {
    var view = this;
    var tab = ui.panel.id;
    if (tab == 'devices_tab') {
      Api.get(this.model.get('volume').resource_uri, {}, function(data) {
        var storage_resource_uri = data.storage_resource;
        var storage_resource_id = storage_resource_uri.split("/")[3];
        Api.get('/api/storage_resource/', {ancestor_of: storage_resource_id}, function(data) {
          var template = _.template($('#storage_resource_list_template').html());
          var storage_resources = data.objects;

          // Filter out device nodes
          var filtered_storage_resources = [];
          _.each(storage_resources, function(resource) {
            if (!_.include(resource.parent_classes, "DeviceNode")) {
              filtered_storage_resources.push(resource);
            }
          });


          var markup = template({'storage_resources': filtered_storage_resources});
          $(view.el).find('#devices_tab').html(markup);
        });
      });
    }
  },
  events: {
    "click .conf_param_apply": "conf_param_apply",
    "click .conf_param_reset": "conf_param_reset",
    'click .conf_param_cancel': 'conf_param_cancel'
  }
});
