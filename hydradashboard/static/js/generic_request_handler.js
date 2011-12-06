/*******************************************************************************
 * File name: generic_request_handler.js
 * Description: Generic functions required for handling API requests.
 * ------------------ Data Loader functions--------------------------------------
 * 1) invoke_api_call(request_type, api_url, api_args, callback)
 * 2) display_error(data, textStatus, jqXHR, callback_handler)
 * 3) no_handler(api_url, status_code)
/*****************************************************************************/
/********************************************************************************
// Constants for generic API handling
/********************************************************************************/
var API_PREFIX = "/api/";
var standard_error_msg = "An error occured: ";
var no_handler_msg = "No handler for ";
/********************************************************************************
// Generic function that handles API requests 
/********************************************************************************/
function invoke_api_call(request_type, api_url, api_args, callback)
{
  $.ajax({type: request_type, url: API_PREFIX + api_url, dataType: 'json', data: JSON.stringify(api_args),
          contentType:"application/json; charset=utf-8"}
  )
  .success(function(data, textStatus, jqXHR)
  {
    if(typeof(callback) == "function")
      callback(data);
    else
    {
      var status_code = jqXHR.status;
      if(callback[status_code] != undefined)
        callback[status_code](data);
      else
        no_handler(api_url, status_code);
    }
  })
  .error(function(data, textStatus, jqXHR)
  {
    if(typeof(callback) == "function")
      callback(data);
    else
    {
      var status_code = jqXHR.status;
      if(callback[status_code] != undefined)
        callback[status_code](data);
      else
        no_handler(api_url, status_code);
    }
  })
  .complete(function(event)
  {
  });
}
/********************************************************************************
// Function to display error messages
/********************************************************************************/
function display_error(data, textStatus, jqXHR, callback_handler)
{
  var parsed_response = jQuery.parseJSON(data.responseText);
  var error_message = parsed_response.errors;
  $.jGrowl(standard_error_msg + error_message , { sticky: true });
}
/********************************************************************************
// Function to display error message when no handler for success/error code is specified 
/********************************************************************************/
function no_handler(api_url, status_code)
{
  $.jGrowl(standard_error_msg + no_handler_msg + api_url + ":" + status_code , { sticky: true });
}
/********************************************************************************/
