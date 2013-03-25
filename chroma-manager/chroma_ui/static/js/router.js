//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


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
      "user": "/configure/user",
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

/* FIXME: if router callbacks throw an exception when called
 * as a result of Backbone.history.navigate({trigger:true}),
 * the exception isn't visible at the console, and the URL
 * just gets appended to window.location.href.  Is this a
 * backbone bug?  Should we override History to fix this?
 */
var ChromaRouter = Backbone.Router.extend({
  routes: {
    "configure/filesystem/detail/:id/": "filesystemDetail",
    "configure/filesystem/list/": "filesystemList",
    "configure/filesystem/create/": "filesystemCreate",
    "configure/:tab/": "configure",
    "configure/": "configureIndex",
    "dashboard/": "dashboard",
    "dashboard/:type/": "dashboard_type",
    "dashboard/filesystem/:filesystem_id/": "dashboard_filesystems",
    "dashboard/filesystem/:filesystem_id/target/:target_id/": "dashboard_filesystems",
    "dashboard/server/:server_id/": "dashboard_servers",
    "dashboard/server/:server_id/target/:target_id/": "dashboard_servers",
    "command/:id/": 'command_detail',
    "target/:id/": 'target_detail',
    "host/:id/": 'server_detail',
    "user/:id/": 'user_detail',
    "storage_resource/:id/": 'storage_resource_detail',
    "job/:id/": 'job_detail',
    "": "dashboard",
    "alert/": "alert",
    "event/": "event",
    "log/": "log",
    "about/": "about",
    "status/": "status",
    "system_status/": "system_status"
  },
  object_detail: function(id, model_class, view_class, title_attr)
  {
    var c = new model_class({id: id});
    c.fetch({success: function(model, response) {
      // Remove existing dialog if present, create a new one.
      var dialog_id = view_class.prototype.className + "_" + id;
      $('#' + dialog_id).remove();
      var mydiv = $("<div id='" + dialog_id + "' style='overflow-y: scroll;'></div>");

      var title;
      if (title_attr){
        title = c.get(title_attr);
      } else {
        title = undefined;
      }
      mydiv.dialog({
        buttons: [{text: "Close", 'class': "close", click: function(){
          $(this).dialog('close');
        }}],
        close: function(event, ui) {
          window.history.back();
          $(this).remove();
        },
        width: 600,
        height: 600,
        modal: true,
        title: title
      });
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
    this.object_detail(id, Target, TargetDetail, 'label');
  },
  storage_resource_detail: function(id)
  {
    this.object_detail(id, StorageResource, StorageResourceDetail, 'class_name');
  },
  job_detail: function(id)
  {
    this.object_detail(id, Job, JobDetail, 'description');
  },
  server_detail: function(id)
  {
    this.object_detail(id, Server, ServerDetail, 'label');
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
  log: function()
  {
    this.toplevel('log');
  },
  about:function () {
    this.toplevel('about');
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
    this.navigate('dashboard/',{replace: true});
    this.dashboard();
    return true;
  },
  configureIndex: function()
  {
    if ( this.failed_filesystem_admin_check() )
      return;
    this.filesystemList();
  },
  toplevel: function(name)
  {
    $('div.toplevel').hide();
    $("#toplevel-" + name).show();

    $('a.navigation').removeClass('active');
    $("#" + name + "_menu").addClass('active');

    if (name == 'alert') {
      AlertView.draw();
    } else if (name == 'event') {
      EventView.draw();
    } else if (name == 'log') {
      LogView.draw();
    }

    // FIXME: generalise this once there is a global ChartManager
    if (name != 'dashboard') {
      Dashboard.stopCharts();
    }
  },
  configureTab: function(tab)
  {
    this.toplevel('configure');
    $("#tabs").tabs('select', '#' + tab + "-tab");
  },
  configure: function(tab) {
    if ( this.failed_filesystem_admin_check() )
      return;
    this.configureTab(tab);
    if (tab == 'filesystem') {
      this.filesystemList();
    } else if (tab == 'server') {
      ServerView.draw()
    } else if (tab == 'volume') {
      VolumeView.draw()
    } else if (tab == 'user') {
      UserView.draw()
    } else if (tab == 'storage') {
      StorageView.draw()
    } else if (tab == 'mgt') {
      MgtView.draw()
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
    FilesystemDetailView.draw(id)
  },
  filesystemCreate: function() {
    if ( this.failed_filesystem_admin_check() )
      return;
    this.filesystemPage('create');
    FilesystemCreateView.draw()
  },
  dashboard: function() {
    this.dashboard_type('filesystem');
  },
  dashboard_type: function(type) {
    this.toplevel('dashboard');
    Dashboard.setPath(type);
  },
  dashboard_servers: function(server_id, target_id) {
    this.toplevel('dashboard');
    Dashboard.setPath('server', server_id, target_id);
  },
  dashboard_filesystems: function(filesystem_id, target_id) {
    this.toplevel('dashboard');
    Dashboard.setPath('filesystem', filesystem_id, target_id);
  }
});
