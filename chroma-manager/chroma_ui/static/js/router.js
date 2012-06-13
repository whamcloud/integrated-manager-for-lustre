//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================



function uri_properties_link(resource_uri, label)
{
  if (resource_uri) {
    var url = resource_uri.replace("/api/", "/");
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
    "storage_resource/:id/": 'storage_resource_detail',
    "job/:id/": 'job_detail',
    "": "dashboard",
    "alert/": "alert",
    "event/": "event",
    "log/": "log",
    "about/": "about"
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
          $(this).remove();
          window.history.back();
        }}],
        width: 600,
        height: 600,
        modal: true,
        title: title,
        open: function(event, ui) {
          // Hide the window close button to have a single close handler
          // (the button) which manages history.
          mydiv.parent().find('.ui-dialog-titlebar-close').hide();
        }
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
  configureIndex: function()
  {
    this.filesystemList()
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
    this.filesystemPage('list');
    FilesystemListView.draw()
  },
  filesystemDetail: function(id) {
    this.filesystemPage('detail');
    FilesystemDetailView.draw(id)
  },
  filesystemCreate: function() {
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
