/*******************************************************************************
 * File name: generic_request_handler.js
 * Description: Generic functions required for handling API requests.
 * ------------------ Data Loader functions--------------------------------------
 * 1) invoke_api_call(request_type, api_url, api_args, callback)
 * 2) unexpected_error(data)
/*****************************************************************************
 * API Type Constants
******************************************************************************/
var api_get = "GET";
var api_post = "POST";
var api_put = "PUT";
var api_delete = "DELETE";
/********************************************************************************
// Constants for generic API handling
/********************************************************************************/
var API_PREFIX = "/api/";


var outstanding_requests = 0;

function start_blocking()
{
  if (disable_api) {
    return;
  }

  outstanding_requests += 1;
  if (outstanding_requests == 1) {
    $.blockUI({
      message: ""
    });
  }
}

function complete_blocking()
{
  if (disable_api) {
    return;
  }

  outstanding_requests -= 1;
  if (outstanding_requests == 0) {
    $.unblockUI();
  }
}

var disable_api = false;

/********************************************************************************
// Generic function that handles API requests 
/********************************************************************************/
function invoke_api_call(request_type, api_url, api_args, success_callback, error_callback, blocking)
{
  if (disable_api) {
    return;
  }

  if (blocking == undefined) {
    blocking = true;
  }

  var ajax_args;
  if (request_type == api_get) {
    ajax_args = {
      type: request_type,
      url: API_PREFIX + api_url,
      data: api_args
    }
  } else {
    ajax_args = {
      type: request_type,
      url: API_PREFIX + api_url,
      dataType: 'json',
      data: JSON.stringify(api_args),
      contentType:"application/json; charset=utf-8"}
    }

  if (blocking) {
    start_blocking();
  }
  $.ajax(ajax_args)
  .success(function(data, textStatus, jqXHR)
  {
    if (success_callback) {
      if(typeof(success_callback) == "function") {
        /* If success_callback is a function, call it */
        success_callback(data);
      } else {
        /* If success_callback is not a function, assume it
           is a lookup object of response code to callback */
        var status_code = jqXHR.status;
        if(success_callback[status_code] != undefined) {
          success_callback[status_code](data);
        } else {
          /* Caller gave us a lookup table of success callbacks
             but we got a response code that was successful but
             unhandled -- consider this a bug or error */ 
          api_unexpected_error(data, textStatus, jqXHR);
        }
      }
    }
  })
  .error(function(jqXHR, textStatus)
  {
    if (error_callback) {
      if(typeof(error_callback) == "function") {
        /* Caller has provided a generic error handler */
        error_callback(jqXHR.responseText);
      } else if(typeof(error_callback) == "object") {
        var status_code = jqXHR.status;
        if(error_callback[status_code] != undefined) {
          /* Caller has provided handler for this status */
          error_callback[status_code](jqXHR.responseText);
        } else {
          /* Caller has provided some handlers, but not one for this
             status code, this is a bug or unhandled error */
          api_unexpected_error(textStatus, jqXHR);
        }
      }
    } else {
      /* Caller has provided no error handlers, this is a bug
         or unhandled error */
      api_unexpected_error(textStatus, jqXHR);
    }
  })
  .complete(function(event)
  {
    if (blocking) {
      complete_blocking();
    }
  });
}
/********************************************************************************
//Function to display generic error message 
/********************************************************************************/
function api_unexpected_error(textStatus, jqXHR)
{
  console.log("unexpected_error: " + textStatus);
  console.log(jqXHR);
  disable_api = true;
  var message = "We are sorry, but something has gone wrong.";
  message += "<dl>";
  message += "<dt>Status:</dt><dd>" + jqXHR.status + "(" + textStatus + ")" + "</dd>";
  message += "<dt>Response headers:</dt><dd>" + jqXHR.getAllResponseHeaders() + "</dd>";
  message += "<dt>Response body:</dt><dd>" + jqXHR.responseText + "</dd>";
  message += "</dl>";
  message += "<a href='#' onclick='window.location.reload(false);'>Reload</a>"
  $.blockUI({message: message});
}
