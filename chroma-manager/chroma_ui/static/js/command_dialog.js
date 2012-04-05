
/* Subclass of Backbone.Collection which provides
 * methods for working with URIs instead of IDs */
var UriCollection = Backbone.Collection.extend({
  fetch_uris: function(uris, success) {
    var ids = [];
    $.each(uris, function(i, uri) {
      var tokens = uri.split("/")
      var id = tokens[tokens.length - 2]
      ids.push(id);
    });
    if (ids.length) {
      this.fetch({data: {limit: 0, id__in: ids}, success: success})
    } else {
      success()
    }
  }
});

var Job = Backbone.Model.extend({
  urlRoot: "/api/job/"
});

var JobCollection = UriCollection.extend({
  model: Job,
  url: "/api/job/",

})

var Step = Backbone.Model.extend({
  urlRoot: "/api/step/",
});

var StepCollection = UriCollection.extend({
  model: Step,
  url: "/api/step/"
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
    var command_detail_view = this;
    var rendered = this.template(this.model.toJSON());
    $(this.el).find('.ui-dialog-content').html(rendered)
    $(this.el).find('.job_state_transition').each(function() {
      var link = $(this);
      link.button();
      link.click(function(ev) {
        var uri = link.data('job_uri');
        var state = link.data('state');
        console.log(uri);
        console.log(state);
        Api.put(uri, {'state': state},
          success_callback = function(data) {
            command_detail_view.model.fetch({success:function(){
              command_detail_view.render();
            }});
            // TODO: reload the command and its job, and redraw the UI
          }
        );
        ev.preventDefault();
      });
    });
    return this;
  },
  close: function() {
    this.remove();
  }
});


var JobDetail = Backbone.View.extend({
  className: 'job_dialog',
  events: {
    "click button.close": "close"
  },
  template: _.template($('#job_detail_template').html()),
  render: function() {
    var el = $(this.el)
    var model = this.model;
    var template = this.template

    var steps = new StepCollection();
    steps.fetch_uris(model.attributes.steps, function() {
      var job = model.toJSON();
      job.steps = steps.toJSON();
      var wait_for = new JobCollection();

      wait_for.fetch_uris(model.attributes.wait_for, function() {
        job.wait_for = wait_for.toJSON();

        var rendered = template({job: job});
        el.find('.ui-dialog-content').html(rendered)
        el.find('.dialog_tabs').tabs();
        if (job.wait_for.length == 0) {
          el.find('.dialog_tabs').tabs('disable', 'dependencies');
        }
        if (job.steps.length > 1) {
          el.find('.job_step_list').accordion({collapsible: true});
        }
      });
    });

    return this;
  },
  close: function() {
    this.remove();
  }
});

var JobCache = new JobCollection();

