/*******************************************************************************
 * File name: generic_request_handler.js
 * Description: Generic functions required for handling API requests.
 * ------------------ Data Loader functions--------------------------------------
 * 1) invoke_api_call(request_type, api_url, api_args, callback)
 * 2) common_error_handler(data)
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
var standard_error_msg = "An error occured: ";
/********************************************************************************
// Generic function that handles API requests 
/********************************************************************************/
function invoke_api_call(request_type, api_url, api_args, success_callback, error_callback)
{
  var ajax_args;
  if (request_type == api_get) {
    encoded_api_args = {}
    $.each(api_args, function(k, v) {
      encoded_api_args[k] = JSON.stringify(v)
    });
    ajax_args = {
      type: request_type,
      url: API_PREFIX + api_url,
      data: encoded_api_args
    }
  } else {
    ajax_args = {
      type: request_type,
      url: API_PREFIX + api_url,
      dataType: 'json',
      data: JSON.stringify(api_args),
      contentType:"application/json; charset=utf-8"}
    }
  $.ajax(ajax_args)
  .success(function(data, textStatus, jqXHR)
  {
    if(typeof(success_callback) == "function")
      success_callback(data);
    else
    {
      var status_code = jqXHR.status;
      if(success_callback[status_code] != undefined)
        success_callback[status_code](data);
    }
  })
  .error(function(data, textStatus, jqXHR)
  {
    if(typeof(error_callback) == "function")
    {
      error_callback(data);
    }
    else if(typeof(error_callback) == "object")
    {
      var status_code = jqXHR.status;
      if(error_callback[status_code] != undefined)
        error_callback[status_code](data);
      else
        common_error_handler(data);
    }
    else
    {
      common_error_handler(data);
    }
  })
  .complete(function(event)
  {
  });
}
/********************************************************************************
//Function to display generic error message 
/********************************************************************************/
function common_error_handler(data)
{
  if(data.errors != undefined)
  {
    $.jGrowl(standard_error_msg + data.errors , { sticky: true });
  }
}
