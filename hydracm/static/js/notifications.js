
/* notifications: poll the API for new Jobs/Alerts/Events and 
 * trigger jGrowl UI */

var last_check = page_load_time;
var poll_period = 1000;
var error_retry_period = 10000;

var known_jobs = [];
var running_job_count = 0;

update_icon = function() {
  $('#notification_icon_jobs').toggle(running_job_count > 0);
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
        notify = true;
        if (job_info.state != 'complete') {
          args = {header: "Job started"};
          running_job_count += 1;
        } else {
          args = completion_jgrowl_args(job_info);
        }
      } else {
        if (existing.state != 'complete' && job_info.state == 'complete') {
          notify = true;
          args = completion_jgrowl_args(job_info);
          running_job_count -= 1;
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
        running_job_count += 1;
      });
      update_icon();
      setTimeout(poll_jobs, poll_period);
    }
  });
});

