
/* So that Backbone.sync will pass GET list parameters
 * in the way that tastypie requires them */
jQuery.ajaxSetup({traditional: true})
Backbone.base_sync = Backbone.sync
Backbone.sync = function(method, model, options) {
  var outer_success = options.success;
  var outer_this = this;
  options.success = function() {
    var data = arguments[0]
    if (data.meta != undefined && data.objects != undefined) {
      arguments[0] = data.objects;
    }
    outer_success.apply(outer_this, arguments);
  }

  Backbone.base_sync.apply(this, [method, model, options])
}

var Job = Backbone.Model.extend({
  urlRoot: "/api/job/",
  fetch: function(options) {
    var outer_success = options.success;
    options.success = function(model, response) {

    
      if (outer_success) {
        outer_success(model, repsonse)
      }
    }

    Backbone.Model.prototype.fetch.apply(this, [options])
  },

  initialize: function(attributes) {
    var icon;
    if (attributes.state == 'pending') {
      icon = "/static/images/icon_hourglass.png"
    } else if (attributes.state == 'complete') {
      if (attributes.cancelled) {
        icon = "/static/images/gtk-cancel.png"
      } else if (attributes.errored) {
        icon = "/static/images/dialog-error.png"
      } else {
        icon = "/static/images/icon_tick.png"
      }
    } else {
      icon = "/static/images/ajax-loader.gif"
    }
    this.set('icon', icon)
  }
});

var JobCollection = Backbone.Collection.extend({
  model: Job,
  url: "/api/job/"
})

var Command = Backbone.Model.extend({
  jobTree: function(jobs) {
    // For each job ID, the job dict
    var id_to_job = {};
    // For each job ID, which other jobs in this command wait for me
    var id_to_what_waits = {};

    $.each(jobs, function(i, job) {
      id_to_job[job.resource_uri] = job;
      id_to_what_waits[job.resource_uri] = []
    });

    $.each(jobs, function(i, job) {
      $.each(job.wait_for, function (i, job_id) {
        if (id_to_job[job_id]) {
          id_to_what_waits[job_id].push(job.resource_uri);
        }
      });
    });

    var shallowest_occurrence = {};
    function jobChildren(root_job, depth) {
      if (depth == undefined) {
        depth = 0
      } else {
        depth = depth + 1
      }

      if (shallowest_occurrence[root_job.resource_uri] == undefined || shallowest_occurrence[root_job.resource_uri] > depth) {
        shallowest_occurrence[root_job.resource_uri] = depth;
      }

      var children = []
      $.each(root_job.wait_for, function(i, job_id) {
        var awaited_job = id_to_job[job_id]
        if (awaited_job) {
          children.push(jobChildren(awaited_job, depth));
        }
      });
      return $.extend({children: children}, root_job)
    }

    var tree = []
    $.each(jobs, function(i, job) {
      var what_waits = id_to_what_waits[job.resource_uri]
      if (what_waits.length == 0) {
        // Nothing's waiting for me, I'm top level
        tree.push(jobChildren(job))
      }
    });

    // A job may only appear at its highest depth
    // e.g. stop a filesystem stops the MDT, making the filesystem unavailable, which the OST waits for
    // e.g. stop a filesystem stops the OST, making the filesystem unavailable, which the MDT waits for
    function prune(root_job, depth) {
      if (depth == undefined) {
        depth = 0
      } else {
        depth = depth + 1
      }

      $.each(root_job.children, function(i, child) {
        var child_depth = depth + 1;
        if (shallowest_occurrence[child.resource_uri] < child_depth) {
          delete root_job.children[i]
        } else {
          prune(child, depth)
        }
      });
    }

    $.each(tree, function(i, root) {
      prune(root);
    });

    return tree;
  },
  fetch: function(options) {
    var outer_success = options.success;
    options.success = function(model, response) {
      var job_ids = [];
      $.each(model.attributes.jobs, function(i, job_uri) {
        var tokens = job_uri.split("/")
        var job_id = tokens[tokens.length - 2]
        job_ids.push(job_id);
      });
      var collection = new JobCollection()
      if (job_ids.length == 0) {
        model.set('jobs_full', []);
        model.set('jobs_tree', []);
        if (outer_success) {
          outer_success(model, response);
        }
      } else {
        collection.fetch({data: {id__in: job_ids, limit: 0}, success: function(c, r) {
          var jobs = c.toJSON()
          model.set('jobs_full', jobs);
          model.set('jobs_tree', model.jobTree(jobs));
          if (outer_success) {
            outer_success(model, response);
          }
        }})
      }
    }

    Backbone.Model.prototype.fetch.apply(this, [options])
  },
  urlRoot: "/api/command/"
})

var CommandDetail = Backbone.View.extend({
  className: 'command_dialog',
  events: {
    "click button.close": "close"
  },
  template: _.template($('#command_detail_template').html()),
  render: function() {
    var rendered = this.template(this.model.toJSON());
    $(this.el).find('.ui-dialog-content').html(rendered)
    return this;
  },
  close: function() {
    this.remove();
  }
});
