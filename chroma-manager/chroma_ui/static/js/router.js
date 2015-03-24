//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


var RouteUtils = function() {

  function api_path_to_ui_path(resource_uri)
  {
    /* Given an API resource URI for an object,
     return the UI URI for the detail view */
    var resource = resource_uri.split('/')[2];
    var id = resource_uri.split('/')[3];

    if (resource == 'filesystem') {
      return "/configure/filesystem/detail/" + id + "/"
    } else {
      return "/" + resource + "/" + id + "/";
    }
  }

  function detail_path_to_list_path(detail_uri)
  {
    /* Given a detail URI for an object, return the
     list URI for that object type */
    var resource = detail_uri.split('/')[2];

    var resource_to_list_uri = {
      "filesystem": "/configure/filesystem/list/",
      "host": "/configure/server/",
      "volume": "/configure/volume/",
      "user": "/configure/user/",
      "storage_resource": "/configure/storage/"
    };

    /* FIXME: can't do the mapping for a /target/ URI because
     the list view of targets is either the MGT list or the detail
     view of a filesystem depending on the target type */

    return resource_to_list_uri[resource];
  }

  function current_path() {
    /* Use this instead of window.location.href to get a path in the
       form that our routing uses (no leading /ui/) */
    return "/" + window.location.pathname.substr(UI_ROOT.length);
  }

  function uri_properties_link(resource_uri, label)
  {
    if (resource_uri) {
      var url = api_path_to_ui_path(resource_uri);
      return "<a class='navigation' href='" + url + "'>" + label + "</a>"
    } else {
      return ""
    }
  }

  function object_properties_link(object, label)
  {
    if (!label) {
      label = LiveObject.label(object);
    }
    return uri_properties_link(object.resource_uri, label);
  }

  return {
    'api_path_to_ui_path': api_path_to_ui_path,
    'detail_path_to_list_path': detail_path_to_list_path,
    'uri_properties_link': uri_properties_link,
    'object_properties_link': object_properties_link,
    'current_path': current_path
  }
}();

  var routes = {
    'configure/filesystem/detail/:id/': 'filesystemDetail',
    'configure/filesystem/list/': 'filesystemList',
    'configure/filesystem/create/': 'filesystemCreate',
    'configure/:tab/': 'configure',
    'configure/': 'configureIndex',
    'command/:id/': 'command_detail',
    'target/:id/': 'target_detail',
    'user/:id/': 'user_detail',
    'storage_resource/:id/': 'storage_resource_detail',
    'job/:id/': 'job_detail',
    'alert/': 'alert',
    'event/': 'event',
    'log/around-:aroundDatetime/': 'log',
    'log/': 'log',
    'status/': 'status',
    'system_status/': 'system_status'
  };

  routes = Object.keys(routes).reduce(function (newRoutes, route) {
    'use strict';

    newRoutes[route] = newRoutes[route.slice(0, -1)] = routes[route];

    return newRoutes;
  }, {});



/* FIXME: if router callbacks throw an exception when called
 * as a result of Backbone.history.navigate({trigger:true}),
 * the exception isn't visible at the console, and the URL
 * just gets appended to window.location.href.  Is this a
 * backbone bug?  Should we override History to fix this?
 */
var ChromaRouter = Backbone.Router.extend({
  routes: routes,
  conf_param_dialog: null,
  object_detail: function(id, model_class, view_class, title_attr, overridePropertiesFunc)
  {
    var c = new model_class({id: id});
    c.fetch({success: function(model, response) {
      // Remove existing dialog if present, create a new one.
      var dialog_id = view_class.prototype.className + "_" + id;
      $('#' + dialog_id).remove();
      var mydiv = $("<div id='" + dialog_id + "' style='overflow-y: scroll;'></div>");

      var title = (_.isFunction(title_attr)? title_attr(c): c.get(title_attr));

      var properties = {
        buttons: [
          {text: "Close", 'class': "close", click: function () {
            $(this).dialog('close');
          }}
        ],
        close: function (event, ui) {
          window.history.back();
          $(this).dialog('destroy').remove();
        },
        width: 600,
        height: 600,
        modal: true,
        title: title
      };

      properties = (_.isFunction(overridePropertiesFunc)?
        overridePropertiesFunc.bind(null, c): _.identity
      )(properties);

      mydiv.dialog(properties);
      var cd = new view_class({model: c, el: mydiv.parent()});
      cd.render();
    }})
  },
  command_detail: function(id)
  {
    this.object_detail(id, Command, CommandDetail);
  },
  target_detail: function(id)
  {
    this.object_detail(id, Target, TargetDetail, function titleFunc(c) {
      var kinds = {
        MDT: 'Metadata Target',
        MGT: 'Management Target',
        OST: 'Object Storage Target'
      };

      var kind = kinds[c.get('kind')];
      var label = c.get('label');

      return '%s: %s'.sprintf(kind, label);
    },
    function propertyFunc(c, properties) {
      if (c.get('kind') === 'OST') {
        properties.height = 710;
        properties.open = function () {
          $(this).css('overflow', 'hidden');
        }
      }

      return properties;
    });
  },
  storage_resource_detail: function(id)
  {
    this.object_detail(id, StorageResource, StorageResourceDetail, 'class_name');
  },
  job_detail: function(id)
  {
    this.object_detail(id, Job, JobDetail, 'description');
  },
  user_detail: function(id)
  {
    this.object_detail(id, User, UserDetail, 'username');
  },
  alert: function()
  {
    this.toplevel('alert');
  },
  event: function()
  {
    this.toplevel('event');
  },
  log: function(aroundDatetime)
  {
    this.toplevel('log', aroundDatetime);
  },
  status: function () {
    this.toplevel('status');
  },
  system_status:function() {
    this.toplevel('system_status');
    (new SystemStatusView()).render();
  },
  failed_filesystem_admin_check: function() {
    if ( Login.userHasGroup('filesystem_administrators') )
      return false;

    window.location.href = '%sdashboard/'.sprintf(Api.UI_ROOT);
  },
  configureIndex: function()
  {
    if ( this.failed_filesystem_admin_check() )
      return;

    this.configure('filesystem');
  },
  toplevel: function(name, aroundDatetime)
  {
    $('div.toplevel').hide();
    $("#toplevel-" + name).show();
    if (name === 'status') {
      angular.element('html').injector().get('pageTitle').set('Status');
    }

    var navAnchors = $('a.navigation'),
      menuItem = $("#" + name + "_menu");

    navAnchors.removeClass('active');
    navAnchors.parent('li').removeClass('active');
    menuItem.addClass('active');
    menuItem.parent('li').addClass('active');

    if (name == 'alert') {
      AlertView.draw();
    } else if (name == 'event') {
      EventView.draw();
    } else if (name == 'log') {
      LogView.draw(aroundDatetime);
    }
  },
  configureTab: function (tab) {
    this.toplevel('configure');
    var nextTab = $('#' + tab + '-tab');

    $('#toplevel-configure')
      .children('div[id$=tab]').not(nextTab).hide();

    nextTab.show();
  },
  configure: function(tab) {
    if ( this.failed_filesystem_admin_check() )
      return;

    this.configureTab(tab);

    if (tab == 'filesystem') {
      this.filesystemList();
    } else if (tab == 'volume') {
      VolumeView.draw()
    } else if (tab == 'user') {
      UserView.draw()
    } else if (tab == 'storage') {
      StorageView.draw()
    } else if (tab == 'mgt') {
      MgtView.draw()
    } else if (tab === 'power') {
      // NOTE: This is only being done because of the Angular in Backbone paradigm.
      var powerTab = angular.element('#power-tab');
      var powerTabContents = powerTab.contents();
      var $scope = angular.element('html').scope().$new();
      var $compile = $('html').injector().get('$compile');

      $scope.$apply(function () {
        if (powerTabContents.length > 0) {
          powerTabContents.scope().$destroy();
        }

        var link = $compile('<div ng-include="(( config.asStatic(\'partials/power_control.html\') ))"></div>');

        powerTab.html(link($scope));

      });
    }
  },
  filesystemPage: function(page) {
    this.configureTab('filesystem');
    $('#filesystem-tab-list').hide();
    $('#filesystem-tab-create').hide();
    $('#filesystem-tab-detail').hide();
    $('#filesystem-tab-' + page).show();
  },
  filesystemList: function() {
    if ( this.failed_filesystem_admin_check() )
      return;
    this.filesystemPage('list');
    FilesystemListView.draw()
  },
  filesystemDetail: function(id) {
    if ( this.failed_filesystem_admin_check() )
      return;
    this.filesystemPage('detail');
    FilesystemDetailView.draw(id,this)
  },
  filesystemCreate: function() {
    if ( this.failed_filesystem_admin_check() )
      return;
    this.filesystemPage('create');
    FilesystemCreateView.draw(this)
  }
});
