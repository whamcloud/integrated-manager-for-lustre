//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


var ConfParamDialog = function(options) {
  var el = $("<div><div class='help_loader' data-topic='_advanced_settings' /><table class='validated_form' width='100%' border='0' cellspacing='0' cellpadding='0'><thead><th></th><th></th><th></th></thead><tbody></tbody></table></div>");
  var _options = $.extend({}, options);

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

  // initialize (but don't open) settings dialog
  el.dialog
    ({
      autoOpen: false,
      width: 450,
      height: 'auto',
      //maxHeight: $(window).height() - 100,
      modal: true,
      position:"center",
      buttons:
      {
        "Apply": {
          text: "Apply",
          class: "conf_param_apply_button",
          click: function(){
            var datatable = $(this).find('table').dataTable();
            var dialog = $(this);
            if (_options.object) {
              apply_config_params(_options.object, datatable, function() {dialog.dialog('close')});
            } else {
              dialog.dialog('close');
            }
          }
        },
        "Close": {
            text: "Close",
            class: "conf_param_close_button",
            click: function(){
                $(this).dialog('close')
            }
        }
      }
    });

  //populate help snippets
  ContextualHelp.load_snippets(el.find('div').first());

  function open() {
    el.find('span.error').remove();
    el.find('input').removeClass('error');
    el.dialog('open');
  }

  function get() {
    var oSetting = el.find('table').dataTable().fnSettings();
    var result = {};

    for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {
      var conf_param_name = oSetting.aoData[i]._aData[3];
      // If conf_param_name is null, this is one of the title rows not
      // a data row.
      if (conf_param_name) {
        var input_val = $("input[id='conf_param_" + conf_param_name + "']").val();
        if(oSetting.aoData[i]._aData[2] != input_val)
        {
          result[conf_param_name] = $.trim(input_val);
        }
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

  function get_datatable() {
    return el.find('table').dataTable();
  }

  return {
    open: open,
    get: get,
    get_datatable: get_datatable,
    clear: clear
  }
};


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
    sections[section].entries.push([ setting_label, property_box, value, key]);
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
    var conf_param_name = oSetting.aoData[i]._aData[3];
    datatable.find("input[id='conf_param_" + conf_param_name + "']").val(oSetting.aoData[i]._aData[2]);
  }
}

function conf_param_errors(datatable, errors)
{
  $.each(errors, function(k, v){
    var input = datatable.find("input[id='conf_param_" + k + "']");
    input.addClass('error');
    input.before("<span class='error'>" + v + "</span>")
  });
}

function conf_param_clear_errors(datatable)
{
  datatable.find('span.error').remove();
  datatable.find('.error').removeClass('error');
}

/* Read modified conf params out of datatable, PUT them to url */
function apply_config_params(object, datatable, callback)
{
  var oSetting = datatable.fnSettings();
  var changed_conf_params = {};
  var dirty = false;
  for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {
    var conf_param_name = oSetting.aoData[i]._aData[3];
    var input_val = $.trim(datatable.find("input[id='conf_param_" + conf_param_name + "']").val());

    if(oSetting.aoData[i]._aData[2] != input_val)
    {
      dirty = true;

      /* Convert UI empty strings to nulls for API */
      if (input_val == "") {
        input_val = null;
      }

      changed_conf_params[conf_param_name] = input_val;
    }
  }

  conf_param_clear_errors(datatable);

  if(dirty) {
      Api.get(object.resource_uri, {}, function(update_object) {
          update_object.conf_params = $.extend(update_object.conf_params, changed_conf_params);
          Api.put(update_object.resource_uri, update_object,
              success_callback = function()
              {
                  // Set the 'original' value to what we just sent
                  for (var i=0, iLen=oSetting.aoData.length; i<iLen; i++) {

                      var conf_param_name = oSetting.aoData[i]._aData[3];

                      // Update the table with the now-applied changes
                      if (_.include(_.keys(changed_conf_params), conf_param_name)) {
                        var val = changed_conf_params[conf_param_name];
                        if (val == null) {
                          val = "";
                        }

                        oSetting.aoData[i]._aData[2] = val;
                        datatable.find("input[id='conf_param_" + conf_param_name + "']").val(val);
                      }
                  }

                  if(callback) {
                    callback();
                  }
              },
              {
                400: function(jqxhr) {
                  var errors = JSON.parse(jqxhr.responseText);
                  if (errors.conf_params) {
                    conf_param_errors(datatable, errors.conf_params);
                    return true;
                  } else {
                    return false;
                  }
                }
              }
          );
      });
  }
}
