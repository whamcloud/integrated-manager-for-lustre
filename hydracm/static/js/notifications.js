
/* notifications: poll the API for new Jobs/Alerts/Events and 
 * trigger jGrowl UI */

var last_check = page_load_time;
var poll_period = 1000;
var error_retry_period = 10000;

var known_jobs = {};
var running_job_count = 0;
var running_jobs = {}

// Map of [id,ct] to map of job IDs holding a lock
var read_locks = {}
var write_locks = {}

var known_alerts = {};
var active_alert_count = 0;
var active_alerts = {}

// Map of [id,ct] to map of alert IDs affecting this object
var alert_effects = {}

var id_counter = 1;
function get_indicator_id()
{
  id_counter += 1;
  return "notifications_" + id_counter;
}

indicator_markup = function(classes) {
  var el = $('<span/>')
  return "<span id='" + get_indicator_id() + "' class='" + classes.join(" ") + "'></span><span class='tooltip-text'></span>";
}

alert_indicator_markup = function(id, content_type_id)
{
  return indicator_markup(['alert_indicator', "alert_indicator_object_id_" + id + "_" + content_type_id])
}

alert_indicator_list_markup = function(id, content_type_id)
{
  return indicator_markup(['alert_indicator', "alert_indicator_list", "alert_indicator_object_id_" + id + "_" + content_type_id])
}

alert_indicator_large_markup = function(id, content_type_id)
{
  return indicator_markup(['alert_indicator', "alert_indicator_large", "alert_indicator_object_id_" + id + "_" + content_type_id])
}

notification_icon_markup = function(id, ct) {
  return indicator_markup(['notification_object_icon', "notification_object_id_" + id + "_" + ct])
}

notification_icons_markup = function(id, ct) {
  return "<span class='notification_icons'>" + alert_indicator_markup(id,ct) + notification_icon_markup(id,ct) + "</span>"
}

function for_class_starting(element, prefix, callback) {
  $.each(element.attr('class').split(" "), function(i, class_name) {
    if (class_name.indexOf(prefix) == 0) {
      callback(class_name)
    }
  });
}

function debug(msg) {
  //console.log(msg);
}

cluetip_tooltip_format = function(element, title, objects, attr)
{
  var tooltip = title;
  tooltip += "<ul>"
  $.each(objects, function(i, obj) {
    tooltip += "<li>" + obj[attr] + "</li>";
  });
  tooltip += "</ul>"

  element.next('.tooltip-text').html(tooltip);
  element.attr('rel', "#" + element.attr('id') + " + .tooltip-text");
  element.cluetip({cluezIndex: 1002, local: true, hideLocal: true});
}

update_alert_indicator = function(element)
{
  for_class_starting(element, 'alert_indicator_object_id_', function(class_name) {
    var parts = class_name.split("_")
    var key = [parts[4], parts[5]];

    var effects = alert_effects[key]
    effect_count = attr_count(effects)
    if (element.hasClass('alert_indicator_list')) {
      var list_markup = "<ul>";
      if (effect_count > 0) {
        $.each(effects, function(alert_id, x) {
          var alert_info = known_alerts[alert_id]
          list_markup += "<li>" + alert_info.message + "</li>"
        });
        list_markup += "</ul>";
        element.html(list_markup);
        element.removeClass('alert_indicator_inactive');
        element.addClass('alert_indicator_active');
      } else {
        element.html("No alerts");
        element.removeClass('alert_indicator_active');
        element.addClass('alert_indicator_inactive');
      }
    } else {
      if (effect_count > 0) {
        if (element.hasClass('alert_indicator_large')) {
          var text = effect_count + ' alert';
          if (effect_count > 1) {
            text += "s";
          }
          element.html(text)
        }
        element.addClass('alert_indicator_active');
        element.removeClass('alert_indicator_inactive');
        
        var alerts = {};
        $.each(effects, function(alert_id, x) {
          alerts[alert_id] = known_alerts[alert_id]
        });
        cluetip_tooltip_format(element, "Alerts", alerts, 'message');
      } else {
        if (element.hasClass('alert_indicator_large')) {
          element.html('No alerts')
        }
        element.addClass('alert_indicator_inactive');
        element.removeClass('alert_indicator_active');
        element.attr('title', 'No alerts');
        element.cluetip({splitTitle: '|', cluezIndex: 1002});
      }
    }
  });
}

update_alert_indicators = function()
{
  $('.alert_indicator').each(function() {
    update_alert_indicator($(this));
  });
}

update_sidebar_icons = function() {
  if (running_job_count > 0) {
    $('#notification_icon_jobs').show()
    cluetip_tooltip_format($('#notification_icon_jobs'), running_job_count + " jobs running:", running_jobs, 'description');
  } else {
    $('#notification_icon_jobs').hide()
  }

  if (active_alert_count > 0) {
    $('#notification_icon_alerts').show()
    cluetip_tooltip_format($('#notification_icon_alerts'), active_alert_count + " alerts active:", active_alerts, 'message');
  } else {
    $('#notification_icon_alerts').hide()
  }
}

activate_alert = function(alert_info) {
  console.log("Alert " + alert_info.id + " activated");
  if (active_alerts[alert_info.id]) {
    throw "Alert " + alert_info.id + " activated twice"
  }

  active_alerts[alert_info.id] = alert_info
  active_alert_count += 1;

  $.each(alert_info.affected, function(i, effectee) {
    if (!alert_effects[effectee]) {
      alert_effects[effectee] = {}
    }
    alert_effects[effectee][alert_info.id] = 1
    $('.alert_indicator_object_id_' + effectee[0] + '_' + effectee[1]).each(function() {
      update_alert_indicator($(this));
    });
  });
}

deactivate_alert = function(alert_info) {
  console.log("Alert " + alert_info.id + " finished");
  if (active_alerts[alert_info.id] == null) {
    throw "Alert " + alert_info.id + " finished but not in active_alerts"
  }

  delete active_alerts[alert_info.id]
  active_alert_count -= 1;

  $.each(alert_info.affected, function(i, effectee) {
    delete alert_effects[effectee][alert_info.id]
    $('.alert_indicator_object_id_' + effectee[0] + '_' + effectee[1]).each(function() {
      update_alert_indicator($(this));
    });
  });
}

start_running = function(job_info) {
  if (running_jobs[job_info.id]) {
    throw "Job " + job_info.id + " started twice"
  }
  debug('start_running: ' + job_info.id);

  running_jobs[job_info.id] = job_info
  running_job_count += 1;

  var keys = {};
  $.each(job_info.read_locks, function(i, lock) {
    var key = [lock.locked_item_id, lock.locked_item_content_type_id];
    debug('start_running: read lock ' + key)
    if (!read_locks[key]) {
      read_locks[key] = {}
    }
    read_locks[key][job_info.id] = 1

    keys[key] = 0;
  });
  $.each(job_info.write_locks, function(i, lock) {
    var key = [lock.locked_item_id, lock.locked_item_content_type_id];
    debug('start_running: write lock ' + key)
    if (!write_locks[key]) {
      write_locks[key] = {}
    }
    write_locks[key][job_info.id] = 1
    keys[key] = 0;
  });

  debug("keys:");
  debug(keys);
  $.each(keys, function(key, x) {
    key = key.split(",")
    debug('selector: ' + '.notification_object_id_' + key[0] + '_' + key[1])
    $('.notification_object_id_' + key[0] + '_' + key[1]).each(function() {
      notification_update_icon(key, $(this));
    });
  });

  debug("start_running: leaving running_jobs state:");
  debug(running_jobs);
  debug(write_locks);
  debug(read_locks);
}

finish_running = function(job_info) {
  if (running_jobs[job_info.id] == null) {
    throw "Job " + job_info.id + " finished but not in running_jobs"
  }

  debug('finish_running: ' + job_info.id);

  debug("ALPHA: leaving running_jobs state:");
  debug(running_jobs);

  delete running_jobs[job_info.id]

  debug("ZULU: leaving running_jobs state:");
  debug(running_jobs);

  running_job_count -= 1;

  var keys = {};
  $.each(job_info.read_locks, function(i, lock) {
    var key = [lock.locked_item_id, lock.locked_item_content_type_id];
    debug('finish_running: read lock ' + key)
    delete read_locks[key][job_info.id]

    keys[key] = 0;
  });
  $.each(job_info.write_locks, function(i, lock) {
    var key = [lock.locked_item_id, lock.locked_item_content_type_id];
    debug('finish_running: write lock ' + key)
    delete write_locks[key][job_info.id]

    keys[key] = 0;
  });

  $.each(keys, function(key, x) {
    key = key.split(",")
    $('.notification_object_id_' + key[0] + '_' + key[1]).each(function() {
      notification_update_icon(key, $(this));
    });
  });

  debug("finish_running: leaving running_jobs state:");
  debug(running_jobs);
}

attr_count = function(obj) {
  var count = 0;
  for (var k in obj) {
    if (obj.hasOwnProperty(k)) {
      ++count;
    }
  }
  return count;
}

notification_update_icon = function(key, element) {
  debug("notification_update_icon:")
  debug(key)
  debug(element)
  var obj_read_locks = read_locks[key]
  var obj_write_locks = write_locks[key]
  if (obj_write_locks && attr_count(obj_write_locks) > 0) {
    element.show();
    element.addClass('busy_icon');
    debug(obj_write_locks)
    var jobs = {}
    $.each(obj_write_locks, function(job_id, x) {
      jobs[job_id] = known_jobs[job_id]
    });
    cluetip_tooltip_format(element, "Ongoing operations: ", jobs, 'description');
  } else if (obj_read_locks && attr_count(obj_read_locks) > 0) {
    element.show();
    element.addClass('locked_icon');
    var jobs = {}
    $.each(obj_read_locks, function(job_id, x) {
      jobs[job_id] = known_jobs[job_id]
    });
    cluetip_tooltip_format(element, "Locked by pending operations: ", jobs, 'description');
  } else {
    element.removeClass('locked_icon');
    element.removeClass('busy_icon');
  }
}

notification_update_icons = function() {
  $('.notification_object_icon').each( function() {
    var icon_element = $(this);
    for_class_starting($(this), 'notification_object_id_', function(class_name) {
      var parts = class_name.split("_")
      var key = [parts[3], parts[4]];
      notification_update_icon(key, icon_element);
    });
  });
}


update_objects = function(data, silent) {
  $.each(data.response.jobs, function(i, job_info) {
    existing = known_jobs[job_info.id]
    known_jobs[job_info.id] = job_info

    if (data.response.last_modified) {
      last_check = data.response.last_modified;
    }

    function completion_jgrowl_args(info) {
      if (job_info.cancelled) {
        return {header: "Job cancelled", theme: 'job_cancelled'}
      } else if (job_info.errored) {
        return {header: "Job failed", theme: 'job_errored'}
      } else {
        return {header: "Job complete", theme: 'job_success'}
      }
    }

    // Map backend states to a simple
    //  * pending
    //  * running
    //  * complete
    function simple_state(backend_state) {
      if (backend_state == 'pending') {
        return 'pending';
      } else if (backend_state == 'tasked' || backend_state == 'completing' || backend_state == 'cancelling' || backend_state == 'paused' || backend_state == 'tasking') {
        return 'running';
      } else if (backend_state == 'complete') {
        return 'complete';
      } else {
        throw "Unknown job state '" + backend_state + "'";
      }
    }

    var state = simple_state(job_info.state)

    var notify = false;
    var args;
    if (existing == null) {
      if (state != 'complete') {
        start_running(job_info)
      }

      if (state == 'running') {
        notify = true;
        args = {header: "Job started"};
      } else if (state == 'complete') {
        notify = true;
        args = completion_jgrowl_args(job_info);
      }
    } else {
      var old_state = simple_state(existing.state)
      if (state == 'complete' && old_state != 'complete') {
        finish_running(job_info);

        notify = true;
        args = completion_jgrowl_args(job_info);
      } else if (state == 'running' && old_state != 'running') {
        notify = true;
        args = {header: "Job started"};
      }
    }

    if (notify && !silent) {
      $.jGrowl(job_info.description, args);
    }
  });

  $.each(data.response.alerts, function(i, alert_info) {
    existing = known_alerts[alert_info.id]
    known_alerts[alert_info.id] = alert_info

    var notify = false;
    var jgrowl_args;
    if (existing == null) {
      if (alert_info.active) {
        notify = true
        jgrowl_args = {header: "Alert raised", theme: 'alert_raised'}
        activate_alert(alert_info);
      } else {
        /* Learned about a new alert after it had already
         * been raised and lowered */
        notify = true
        jgrowl_args = {header: "Alert cleared"}
      }
    } else {
      if (!(alert_info.active) && existing.active) {
        notify = true
        jgrowl_args = {header: "Alert cleared"}
        deactivate_alert(alert_info);
      }
    }
    if (notify && !silent) {
      $.jGrowl(alert_info.message, jgrowl_args);
    }
  });
}

poll_jobs = function() {
  /* FIXME: using POST instead of GET because otherwise jQuery forces the JSON payload to
   * be urlencoded and django-piston doesn't get our args out properly */
  invoke_api_call(api_post, "notifications/", {filter_opts: {since_time: last_check, initial: false}}, 
  success_callback = function(data)
  {
    update_objects(data);
    update_sidebar_icons();

    setTimeout(poll_jobs, poll_period);
  },
  error_callback = function(data)
  {
    debug("Error calling jobs_since")
    setTimeout(poll_jobs, error_retry_period);
  });
}

object_name_markup = function(id, ct, name) {
  return "<span class='object_name object_name_" + id + "_" + ct + "'>" + name + "</span>";
}

object_state_markup = function(id, ct, state) {
  return "<span class='object_state object_state_" + id + "_" + ct + "'>" + state + "</span>";
}

poll_objects = function() {
  /* Hash which will become a list (ghetto set) */
  var objects = {}
  /* TODO: check other object_* so that something doesn't have to have transitions
   * to be included in the update */
  $('.object_transitions').each(function() {
    for_class_starting($(this), 'object_transitions_', function(class_name){
      var parts = class_name.split("_");
      var key = [parts[2], parts[3]]
      var value = {id: parts[2], content_type_id: parts[3]}
      objects[key] = value
    });
  });
  var object_list = [];
  $.each(objects, function(key, value) {
    object_list.push(value);
  });
  
  /* FIXME: using POST instead of GET because otherwise jQuery forces the JSON payload to
   * be urlencoded and django-piston doesn't get our args out properly */
  invoke_api_call(api_post, "object_summary/", {objects: object_list}, 
  success_callback = function(data)
  {
    setTimeout(poll_objects, poll_period);
    $.each(data.response, function(i, object_info) {
      /* TODO: only rewrite markup on change */
      $(".object_transitions_" + object_info.id + "_" + object_info.content_type_id).replaceWith(
        CreateActionLink(object_info.id, object_info.content_type_id, object_info.available_transitions, ""));
      $(".object_name_" + object_info.id + "_" + object_info.content_type_id).html(object_info.label)
      $(".object_state_" + object_info.id + "_" + object_info.content_type_id).html(object_info.state)
    });
  },
  error_callback = function(data)
  {
    debug("Error calling object_summary")
    setTimeout(poll_objects, error_retry_period);
  });
}

$(document).ready(function() {
  invoke_api_call(api_post, "notifications/", {filter_opts: {since_time: "", initial: true}}, 
  success_callback = function(data)
  {
    update_objects(data, silent = true);
    update_sidebar_icons();
    setTimeout(poll_jobs, poll_period);
  },
  error_callback = function(data){
  });
  
  setTimeout(poll_objects, poll_period);
});

$(document).ajaxComplete(update_alert_indicators)
$(document).ajaxComplete(notification_update_icons)


