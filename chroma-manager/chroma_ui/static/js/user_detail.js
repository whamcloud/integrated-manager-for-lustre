//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var User = Backbone.Model.extend({
  urlRoot: "/api/user/"
});

var UserAlertSubscriptions = function() {
  // Simple caching -- api_cache.js won't work because AlertType is a
  // synthetic resource (no table behind it, so no queryset to cache).
  var alert_types = _fetch_types();

  function _safe_name(description) {
    return description.toLowerCase().replace(/\s+/g,"_");
  }

  function _fetch_types() {
    var fetched_types = {};

    Api.get("/api/alert_type/", {limit: 0}, success_callback = function(data) {
      _.each(data.objects, function(type) {
        type.safe_name = _safe_name(type.description);
        fetched_types[type.id] = type;
      })
    });

    return fetched_types;
  }

  function _subscribed_type_ids(user) {
    return _.pluck(_.pluck(user.get('alert_subscriptions'), 'alert_type'), 'id');
  }

  function _type_name_to_id(alert_type_name) {
    return _.find(alert_types,
                  function(type){return type.safe_name === alert_type_name}).id;
  }

  function get(user) {
    var type_subscriptions = {};

    _.each(alert_types, function(type, id) {
      if (_.include(_subscribed_type_ids(user), id)) {
        type_subscriptions[id] = {'type': type, 'subscribed': true};
      } else {
        type_subscriptions[id] = {'type': type, 'subscribed': false};
      }
    });

    return type_subscriptions;
  }

  function set(user, selections, callback) {
    var to_delete = [];
    var to_add = [];

    _.each(user.get('alert_subscriptions'), function(s) {
      var alert_name = _safe_name(s.alert_type.description);
      if (!(_.include(selections, alert_name))) {
        to_delete.push(s.resource_uri);
      }
    });

    _.each(selections, function(type_name) {
      var type_id = _type_name_to_id(type_name);
      if (!(_.include(_subscribed_type_ids(user), type_id))) {
        to_add.push(
          {user: user.get('resource_uri'),
           alert_type: alert_types[type_id].resource_uri}
        );
      }
    });

    if (to_delete.length > 0 || to_add.length > 0) {
      Api.patch('/api/alert_subscription/', {objects: to_add,
                                             deleted_objects: to_delete},
                success_callback = function(status, jqXHR) {
                  if (callback) {
                    callback();
                  }
                }
      );
    }
  }

  return {
    get: get,
    set: set
  }
}();

var UserDetail = Backbone.View.extend({
  className: 'user_detail',
  template: _.template($('#user_detail_template').html()),
  render: function() {
    var rendered = this.template({'user': this.model.toJSON()});
    var view = this;
    $(this.el).find('.ui-dialog-content').html(rendered);
    $(this.el).find('.tabs').tabs({'show': function(event, ui) {view.tab_select(event, ui)}});

    return this;
  },
  events: {
    "click button.save_user": "save_user",
    "click button.reset_user": "reset_user",
    "click button.change_password": "change_password",
    "click button.clear_subscriptions": "clear_subscriptions",
    "click button.select_all_subscriptions": "select_all_subscriptions",
    "click button.update_subscriptions": "update_subscriptions",
    "click button.reset_subscriptions": "reset_subscriptions"
  },
  save_user: function() {
    var view = this;
    ValidatedForm.save($(this.el).find(".user_detail_form"), Api.put, this.model.get('resource_uri'), this.model.toJSON(), function() {
      $(view.el).find('#user_save_result').html("Changes saved successfully.");
      // Ensure that the model is updated for other tabs.
      view.model.fetch();
    });
  },
  reset_user: function() {
    ValidatedForm.reset($(this.el).find(".user_detail_form"), this.model);
  },
  change_password: function() {
    var view = this;
    ValidatedForm.save($(this.el).find(".user_password_form"), Api.put, this.model.get('resource_uri'), this.model.toJSON(), function() {
      ValidatedForm.clear($(view.el).find(".user_password_form"));
      $(view.el).find('#password_change_result').html("Password updated successfully.");
    });
  },
  display_subscriptions: function(subscriptions) {
    var view = this;
    var markup = _.template($('#user_alert_subs_form').html())({subscriptions: subscriptions});
    $(view.el).find('#user_alert_subs_tab').html(markup);
    $(view.el).find('#user_alert_subs_tab').find('button').button();
  },
  clear_subscriptions: function() {
    var user = this.model;
    var subscriptions = UserAlertSubscriptions.get(user);
    _.each(subscriptions, function(vals, id) {vals.subscribed = false});
    this.display_subscriptions(subscriptions);
  },
  select_all_subscriptions: function() {
    var user = this.model;
    var subscriptions = UserAlertSubscriptions.get(user);
    _.each(subscriptions, function(vals, id) {vals.subscribed = true});
    this.display_subscriptions(subscriptions);
  },
  reset_subscriptions: function() {
    // Just re-draw the tab
    var user = this.model;
    var subscriptions = UserAlertSubscriptions.get(user);
    this.display_subscriptions(subscriptions);
  },
  update_subscriptions: function() {
    var view = this;
    var user = this.model;
    var form = $(view.el).find('#user_alerts_form');
    var selections = [];

    _.each(form.find("input[type=checkbox]:checked"), function(cb) {
      selections.push(cb.name);
    });

    UserAlertSubscriptions.set(user, selections, function() {
      // refresh the model to update the list of alert subscriptions
      user.fetch();
      $(view.el).find('#subscriptions_change_result').html("Subscriptions updated successfully.");
    });
  },
  tab_select: function(event, ui) {
    var tab = ui.panel.id;
    var user = this.model;

    if (tab == 'user_alert_subs_tab') {
      var subscriptions = UserAlertSubscriptions.get(user);
      this.display_subscriptions(subscriptions);
    }
  }
});
