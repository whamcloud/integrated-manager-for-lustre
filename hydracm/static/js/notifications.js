
/* notifications: poll the API for new Jobs/Alerts/Events and 
 * trigger jGrowl UI */

var last_check = page_load_time;
var poll_period = 1000;
var error_retry_period = 10000;

var known_jobs = [];
var running_job_count = 0;
var running_jobs = {}

var read_locks = {}
var write_locks = {}

update_icon = function() {
  $('#notification_icon_jobs').toggle(running_job_count > 0);
}

start_running = function(job_info) {
  if (running_jobs[job_info.id]) {
    throw "Job " + job_info.id + " started twice"
  }
  console.log('start_running: ' + job_info.id);

  running_jobs[job_info.id] = job_info
  running_job_count += 1;

  var keys = {};
  $.each(job_info.read_locks, function(i, lock) {
    var key = [lock.locked_item_id, lock.locked_item_content_type_id];
    console.log('start_running: read lock ' + key)
    if (!read_locks[key]) {
      read_locks[key] = []
    }
    read_locks[key][job_info.id] = 1

    keys[key] = 0;
  });
  $.each(job_info.write_locks, function(i, lock) {
    var key = [lock.locked_item_id, lock.locked_item_content_type_id];
    console.log('start_running: write lock ' + key)
    if (!write_locks[key]) {
      write_locks[key] = []
    }
    write_locks[key][job_info.id] = 1
    keys[key] = 0;
  });

  $.each(keys, function(key, x) {
    $('.notification_object_id_' + key.id + '_' + key.ct).each(function() {
      notification_update_icon(key, $(this));
    });
  });

  console.log("start_running: leaving running_jobs state:");
  console.log(running_jobs);
}

finish_running = function(job_info) {
  if (running_jobs[job_info.id] == null) {
    throw "Job " + job_info.id + " finished but not in running_jobs"
  }

  console.log('finish_running: ' + job_info.id);

  console.log("ALPHA: leaving running_jobs state:");
  console.log(running_jobs);
  delete running_jobs[job_info.id]

  console.log("ZULU: leaving running_jobs state:");
  console.log(running_jobs);

  running_job_count -= 1;

  var keys = {};
  $.each(job_info.read_locks, function(i, lock) {
    var key = [lock.locked_item_id, lock.locked_item_content_type_id];
    console.log('finish_running: read lock ' + key)
    delete read_locks[key][job_info.id]

    keys[key] = 0;
  });
  $.each(job_info.write_locks, function(i, lock) {
    var key = [lock.locked_item_id, lock.locked_item_content_type_id];
    console.log('finish_running: write lock ' + key)
    delete write_locks[key][job_info.id]

    keys[key] = 0;
  });

  $.each(keys, function(key, x) {
    $('.notification_object_id_' + key.id + '_' + key.ct).each(function() {
      notification_update_icon(key, $(this));
    });
  });

  console.log("finish_running: leaving running_jobs state:");
  console.log(running_jobs);
}



notification_update_icon = function(key, element) {
  var obj_read_locks = read_locks[key]
  var obj_write_locks = write_locks[key]
  if (obj_write_locks && obj_write_locks.length > 0) {
    element.show();
    element.addClass('busy_icon');
  } else if (obj_read_locks && obj_read_locks.length > 0) {
    element.show();
    element.addClass('locked_icon');
  } else {
    element.removeClass('locked_icon');
    element.removeClass('busy_icon');
    element.hide();
  }
}

notification_update_icons = function() {
  $('.notification_object_icon').each( function() {
    var icon_element = $(this);
    $.each($(this).attr('class').split(" "), function(i, class_name) {
      if (class_name.indexOf('notification_object_id_') == 0) {
        parts = class_name.split("_")
        var key = [parts[3], parts[4]];
        notification_update_icon(key, icon_element);
      }
    });
  });
}

poll_jobs = function() {
  /* FIXME: using POST instead of GET because otherwise jQuery forces the JSON payload to
   * be urlencoded and django-piston doesn't get our args out properly */
  $.ajax({type: 'POST', url: "/api/jobs/", dataType: 'json', data: JSON.stringify({filter_opts: {since_time: last_check, incomplete: false}}), contentType:"application/json; charset=utf-8"})
  .success(function(data, textStatus, jqXHR) {
    if (!data.success) {
      console.log("Error calling jobs_since")
      setTimeout(poll_jobs, error_retry_period);
      return;
    }

    if (data.response.last_modified) {
      last_check = data.response.last_modified;
    }

    $.each(data.response.jobs, function(i, job_info) {
      existing = known_jobs[job_info.id]

      function completion_jgrowl_args(info) {
        if (job_info.cancelled) {
          return {header: "Job cancelled", theme: 'job_cancelled'}
        } else if (job_info.errored) {
          return {header: "Job failed", theme: 'job_errored'}
        } else {
          return {header: "Job complete", theme: 'job_success'}
        }
      }

      var notify = false;
      var args;
      if (existing == null) {
        if (job_info.state == 'tasked') {
          notify = true;
          args = {header: "Job started"};
          start_running(job_info)
        } else if (job_info.state == 'complete') {
          /*finish_running(job_info)*/
          notify = true;
          args = completion_jgrowl_args(job_info);
        }
      } else {
        if (existing.state != 'complete' && job_info.state == 'complete') {
          notify = true;
          args = completion_jgrowl_args(job_info);
          finish_running(job_info);
        } else if (existing.state != 'tasked' && job_info.state == 'tasked') {
          notify = true;
          args = {header: "Job started"};
          start_running(job_info);
        }
      }

      if (notify) {
        $.jGrowl(job_info.description, args);
      }
      update_icon();

      known_jobs[job_info.id] = job_info
    });

    setTimeout(poll_jobs, poll_period);
  })
}

$(document).ready(function() {

  $.ajax({type: 'POST', url: "/api/jobs/", dataType: 'json', data: JSON.stringify({filter_opts: {since_time: "", incomplete: true}}), contentType:"application/json; charset=utf-8"})
  .success(function(data, textStatus, jqXHR) {
    if (data.success) {
      if (data.response.last_modified) {
        last_check = data.response.last_modified;
      }
      $.each(data.response.jobs, function(i, job_info) {
        known_jobs[job_info.id] = job_info;
        start_running(job_info);
      });
      update_icon();
      setTimeout(poll_jobs, poll_period);
    }
  });
});

