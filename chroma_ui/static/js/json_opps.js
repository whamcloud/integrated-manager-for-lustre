
var ConfParamDialog = function(options) {
  var el = $("<div><table width='100%' border='0' cellspacing='0' cellpadding='0'><thead><th>Property</th><th>Value</th><th></th></thead><tbody></tbody></table></div>");
  var _options = $.extend({}, options)

  el.find('table').dataTable( {
    "iDisplayLength":30,
    "bProcessing": true,
    "bJQueryUI": true,
    "bPaginate" : false,
    "bSort": false,
    "bFilter" : false,
    "bAutoWidth":false,
    "aoColumns": [
      { "sClass": 'txtleft' },
      { "sClass": 'txtcenter' },
      { "bVisible": false } 
    ]
  });
  el.dialog
  ({
    autoOpen: false,
    width: 450,
    height:470,
    modal: true,
    position:"center",
    buttons: 
    {
      "Apply": function() {
        var datatable = $(this).find('table').dataTable();
        if (_options.url) {
          apply_config_params(_options.url, $(this), datatable);
        }
      },
      "Close": function() { 
        $(this).dialog("close");
      }
    }
  });

  function open() {
    el.dialog('open');
  }

  function set(params) {
    populate_conf_param_table(params, el.find('table'))
  }

  function setHelp(help) {
    var blank_data = {};
    $.each(help, function(name, help) {
      blank_data[name] = null;
    });
    populate_conf_param_table(blank_data, el.find('table'), help)
  }

  function get() {
    var oSetting = el.find('table').dataTable().fnSettings();
    var result = {};
    for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {
      if(oSetting.aoData[i]._aData[2] != $("input#"+i).val()) {
         result[oSetting.aoData[i]._aData[0]] = $("input#"+i).val();
      }
    }
    return result
  }

  function clear() {
    var oSetting = el.find('table').dataTable().fnSettings();
    for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {
      if(oSetting.aoData[i]._aData[2] != $("input#"+i).val()) {
         $("input#"+i).val('');
      }
    }
  }

  return {
    open: open,
    set: set,
    setHelp: setHelp,
    get: get,
    clear: clear
  }
}

stateTransitionCommit = function(url, state)
{
}

$(document).ready(function() {
  $('#transition_confirmation_dialog').dialog({autoOpen: false, maxHeight: 400, maxWidth: 800, width: 'auto', height: 'auto'});
});

stateTransition = function (url, state)
{
  Api.put(url, {dry_run: true, state: state}, 
  success_callback = function(data)  
  {
    var requires_confirmation = false;

    var confirmation_markup = "<p>This action will have the following consequences:</p><ul>";
    if (data.length == 0) {
      // A no-op
      return;
    } else if (data.length > 1) {
      $.each(data, function(i, consequence_info) {
        confirmation_markup += "<li>" + consequence_info.description + "</li>";
        if (consequence_info.requires_confirmation) {
          requires_confirmation = true;
        }
      });
      confirmation_markup += "</ul>"
    } else {
      requires_confirmation = data[0].requires_confirmation;
      confirmation_markup = "<p><strong>" + data[0].description + "</strong></p><p>Are you sure?</p>";
    }

    if (requires_confirmation) {
     $('#transition_confirmation_dialog').html(confirmation_markup);
     $('#transition_confirmation_dialog').dialog('option', 'buttons', {
       'Cancel': function() {$(this).dialog('close');},
       'Confirm': 
       {
           text: "Confirm",
           id: "transition_confirm_button",
           click: function(){
             var dialog = $(this);
             Api.put(url, {state: state}, success_callback = function() {
               dialog.dialog('close');
             })
           }
       }
     });
     $('#transition_confirmation_dialog').dialog('open');
    } else {
      Api.put(url, {state: state})
    }
  });
}


function stateTransitionButtons(stateful_object)
{
  var id = stateful_object.id;
  var ct = stateful_object.content_type_id;
  var available_transitions = stateful_object.available_transitions;

  var ops_action="";
  var action="<span class='transition_buttons' data-resource_uri='" + stateful_object.resource_uri + "'>";
  var button_class = "ui-state-default ui-corner-all";
  $.each(available_transitions, function(i, transition)
  {
    var function_name = "stateTransition(\"" + stateful_object.resource_uri + "\", \"" + transition.state + "\")"
    ops_action = "<button" + " onclick='"+ function_name + "'>" + transition.verb + "</button>&nbsp;";
    action += ops_action;
  });
  action += "</span>"
  return action;
}





function _populate_conf_param_table(data, table, help)
{
  table.dataTable().fnClearTable();
  var property_box="";
  $.each(data, function(key, value)
  {   
    if (value == null) {
      /* TODO: represent nulls as a gray 'unset' state (and display default value)*/
      value = "";
    }
    property_box = "<input type=textbox value='" + value + "' id='conf_param_" + key + 
    "' title='" + help[key] + "' onblur='validateNumber($(this))'/>"; 
    table.dataTable().fnAddData ([
      key, 
      property_box,
      value
    ]);
  });
}

function populate_conf_param_table(data, table, help)
{
  if (help) {
    _populate_conf_param_table(data, table, help);
  } else {
    var keys = [];
    for(var key in data) {
      keys.push(key);
    }
    Api.get("help/conf_param/", {keys: keys.join(",")}, success_callback = function(loaded_help) {
      _populate_conf_param_table(data, table, loaded_help);
    });
  }
}

function validateNumber(el)
{
  if (isNaN(el.val()))
  {
      jAlert("Please enter numeric value");
      el.attr("value","");
      el.focus();
  }
}

/* Read modified conf params out of datatable, PUT them to url, and close dialog_id */
function apply_config_params(url, dialog, datatable)
{
  var oSetting = datatable.fnSettings();
  var changed_conf_params = {}
  var dirty = false;
  for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {
    var conf_param_name = oSetting.aoData[i]._aData[0];
    var input_val = $("input[id='conf_param_" + conf_param_name + "']").val();
    if(oSetting.aoData[i]._aData[2] != input_val)
    {
      dirty = true;
      changed_conf_params[conf_param_name] = input_val;
      /* FIXME: we should set _aData[2] to the value after we submit so that it doesn't
          look changed next time */
    }
  }

  if(dirty)
  {
    var api_params = {
        "conf_params": changed_conf_params,
    };
    Api.put(url, api_params, 
    success_callback = function(data)
    {
      jAlert("Update Successful");
    },
    error_callback = function(data)
    {
      if(data.errors != undefined) {
        jAlert("Error setting Cofiguration Params: " + data.errors);
        return true;
      } else {
        return false;
      }
    });

    dialog.dialog('close'); 
  }
}


