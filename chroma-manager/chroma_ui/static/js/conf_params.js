//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var ConfParamDialog = function(options) {
  var el = $("<div><table width='100%' border='0' cellspacing='0' cellpadding='0'><thead><th></th><th></th><th></th></thead><tbody></tbody></table></div>");
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
            apply_config_params(_options.url, datatable);
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

  var sections = {
    'llite' : { label: 'Tuneable Settings', entries: [] },
    'sys'   : { label: 'Timeout Settings',  entries: [] },
    ''      : { label: 'General Settings',  entries: [] }
  };
  var section_display_order = [ 'llite','sys','' ];
  $.each(data, function(key, value)
  {
    var split_setting = key.split('.');
    var section = split_setting.shift();
    var setting_label = split_setting.join('.');
    // unknown setting groups go to "General"
    if (_.isUndefined(sections[section])) {
      section = '';
    }

    if (value == null) {
      /* TODO: represent nulls as a gray 'unset' state (and display default value)*/
      value = "";
    }
    property_box = "<input type=textbox value='" + _.escape(value) + "' id='conf_param_" + key +
      "' title='" + _.escape(help[key]) + "'/>";
    sections[section].entries.push([ setting_label, property_box, value ]);
  });
  $.each(section_display_order, function() {
    // skip if no entries
    if ( sections[this].entries.length === 0 ) return true;
    table.dataTable().fnAddData( [ '<b>' + _.escape(sections[this].label) + '</b>', '', '' ]);
    table.dataTable().fnAddData( sections[this].entries );
  });
}

function populate_conf_param_table(data, table, help) {

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

function reset_config_params(datatable)
{
  var oSetting = datatable.fnSettings();
  for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {
    var conf_param_name = oSetting.aoData[i]._aData[0];
    $("input[id='conf_param_" + conf_param_name + "']").val(oSetting.aoData[i]._aData[2]);
  }
}

/* Read modified conf params out of datatable, PUT them to url */
function apply_config_params(url, datatable)
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
        // Set the 'original' value to what we just posted
        for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {
          var conf_param_name = oSetting.aoData[i]._aData[0];
          var input_val = $("input[id='conf_param_" + conf_param_name + "']").val();
          oSetting.aoData[i]._aData[2] = input_val
        }
      }
    );
  }
}
