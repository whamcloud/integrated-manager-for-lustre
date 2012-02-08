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

/* Wrap API calls to tastypie paginated methods such that
   jquery.Datatables understands the resulting format */
function datatables_api_call(url, data, callback, settings, kwargs) {
  var kwargs = kwargs;
  if (kwargs == undefined) {
    kwargs = {}
  }
    
  /* Copy datatables args into our dict */
  if (data) {
    $.each(data, function(i, param) {
      kwargs[param.name] = param.value
    });
  }

  /* Rename pagination params from datatables to tastypie */
  if (kwargs.iDisplayLength == -1) {
    kwargs.limit = 0
  } else {
    kwargs.limit = kwargs.iDisplayLength
  }
  delete kwargs.iDisplayLength

  kwargs.offset = kwargs.iDisplayStart
  delete kwargs.iDisplayStart

  invoke_api_call(api_get, url, kwargs, success_callback = function(data) {
    var datatables_data = {}
    datatables_data.aaData = data.objects;
    datatables_data.iTotalRecords = data.meta.total_count
    datatables_data.iTotalDisplayRecords = data.meta.total_count
    callback(datatables_data);
  }, error_callback = null, blocking = false);
}

/********************************************************************************
// Generic function that handles API requests 
/********************************************************************************/
function invoke_api_call(request_type, api_url, api_args, success_callback, error_callback, blocking)
{
  return invoke_api_url(request_type, API_PREFIX + api_url, api_args, success_callback, error_callback, blocking)
}


function invoke_api_url(request_type, url, api_args, success_callback, error_callback, blocking)
{
  if (disable_api) {
    return;
  }

  if (blocking == undefined) {
    blocking = true;
  }

  var ajax_args = {
      type: request_type,
      url: url,
      headers: {
        Accept: "application/json"
      }
  };

  if (request_type == api_get) {
    ajax_args.data = api_args
  } else {
    ajax_args.dataType = 'json'
    ajax_args.data = JSON.stringify(api_args)
    ajax_args.contentType ="application/json; charset=utf-8"
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
        rc = error_callback(jqXHR.responseText);
        if (rc == false) {
          api_unexpected_error(textStatus, jqXHR);
        }
      } else if(typeof(error_callback) == "object") {
        var status_code = jqXHR.status;
        if(error_callback[status_code] != undefined) {
          /* Caller has provided handler for this status */
          rc = error_callback[status_code](jqXHR.responseText);
          if (rc == false) {
            api_unexpected_error(textStatus, jqXHR);
          }
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

/* https://docs.djangoproject.com/en/1.2/ref/contrib/csrf/#csrf-ajax */
$(document).ajaxSend(function(event, xhr, settings) {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }

});

function removeBlankAttributes(obj) {
  $.each(obj, function(attr_name, attr_val) {
    if (attr_val == "") {
      delete obj[attr_name]
    }
  });
  return obj;
}


/* http://snipplr.com/view/5945/ */
function formatNumber(number, decimals, dec_point, thousands_sep) {
    // http://kevin.vanzonneveld.net
    // +   original by: Jonas Raoni Soares Silva (http://www.jsfromhell.com)
    // +   improved by: Kevin van Zonneveld (http://kevin.vanzonneveld.net)
    // +     bugfix by: Michael White (http://crestidg.com)
    // +     bugfix by: Benjamin Lupton
    // +     bugfix by: Allan Jensen (http://www.winternet.no)
    // +    revised by: Jonas Raoni Soares Silva (http://www.jsfromhell.com)    
    // *     example 1: number_format(1234.5678, 2, '.', '');
    // *     returns 1: 1234.57     
 
    var n = number, c = isNaN(decimals = Math.abs(decimals)) ? 2 : decimals;
    var d = dec_point == undefined ? "," : dec_point;
    var t = thousands_sep == undefined ? "." : thousands_sep, s = n < 0 ? "-" : "";
    var i = parseInt(n = Math.abs(+n || 0).toFixed(c)) + "", j = (j = i.length) > 3 ? j % 3 : 0;
 
    return s + (j ? i.substr(0, j) + t : "") + i.substr(j).replace(/(\d{3})(?=\d)/g, "$1" + t) + (c ? d + Math.abs(n - i).toFixed(c).slice(2) : "");
}

/* http://snipplr.com/view/5949/ */
function formatBytes(bytes) {
  if (bytes == null || bytes == undefined) {
    return bytes;
  }

	if (bytes >= 1073741824) {
	     bytes = formatNumber(bytes / 1073741824, 2, '.', '') + 'GB';
	} else { 
		if (bytes >= 1048576) {
     		bytes = formatNumber(bytes / 1048576, 2, '.', '') + 'MB';
   	} else { 
			if (bytes >= 1024) {
    		bytes = formatNumber(bytes / 1024, 0) + 'KB';
  		} else {
    		bytes = formatNumber(bytes, 0) + 'b';
			};
 		};
	};
  return bytes;
}
