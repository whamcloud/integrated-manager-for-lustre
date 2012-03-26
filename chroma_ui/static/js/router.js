

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
    "command/:id/": 'command_detail',
    "job/:id/": 'job_detail',
    "": "dashboard",
    "alert/": "alert",
    "event/": "event",
    "log/": "log",
  },
  command_detail: function(id) 
  {
    var c = new Command({id: id});
    c.fetch({success: function(model, response) {
      var mydiv = $("<div></div>")
      mydiv.dialog({
        buttons: [{text: "Close", class: "close", click: function(){}}],
        width: 400,
        modal: true
      })
      var cd = new CommandDetail({model: c, el: mydiv.parent()});
      cd.render();
    }})
  },
  job_detail: function(id) 
  {
    var j = new Job({id: id});
    j.fetch({success: function(model, response) {
      var dialog = $("<div></div>")
      dialog.dialog({
        buttons: [{text: "Close", class: "close", click: function(){}}],
        width: 600,
        height: 600,
        modal: true
      })
      var view = new JobDetail({model: j, el: dialog.parent()})
      view.render();
    }})
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

    window.title = name + " - Chroma Server"

    if (name == 'alert') {
      AlertView.draw();
    } else if (name == 'event') {
      EventView.draw();
    } else if (name == 'log') {
      LogView.draw();
    }
  },
  configureTab: function(tab)
  {
    this.toplevel('configure');
    $("#tabs").tabs('select', '#' + tab + "-tab");
  },
  configure: function(tab) {
    this.configureTab(tab)
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
    this.configureTab('filesystem')
    $('#filesystem-tab-list').hide()
    $('#filesystem-tab-create').hide()
    $('#filesystem-tab-detail').hide()
    $('#filesystem-tab-' + page).show()
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
    this.toplevel('dashboard');

    loadView(window.location.hash);
    $('#fsSelect').attr("value","");
    $('#intervalSelect').attr("value","");
  }
})
