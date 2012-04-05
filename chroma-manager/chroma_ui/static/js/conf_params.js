
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
          $(this).dialog('close')
        },
        "Close": function() {
          $(this).dialog("close");
        }
      }
    });

  if (_options.conf_params) {
    populate_conf_param_table(_options.conf_params, el.find('table'))
  }

  if (_options.help) {
    var blank_data = {};
    $.each(_options.help, function(name, help) {
      blank_data[name] = null;
    });
    populate_conf_param_table(blank_data, el.find('table'), _options.help)
  }

  function open() {
    el.dialog('open');
  }

  function get() {
    var oSetting = el.find('table').dataTable().fnSettings();
    var result = {};

    for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {
      var conf_param_name = oSetting.aoData[i]._aData[0];
      var input_val = $("input[id='conf_param_" + conf_param_name + "']").val();
      if(oSetting.aoData[i]._aData[2] != input_val)
      {
        result[oSetting.aoData[i]._aData[0]] = input_val;
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
    get: get,
    clear: clear
  }
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
        // Set the 'original' value to what we just posted
        for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {
          var conf_param_name = oSetting.aoData[i]._aData[0];
          var input_val = $("input[id='conf_param_" + conf_param_name + "']").val();
          oSetting.aoData[i]._aData[2] = input_val
        }
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