
var VolumeChooserStore = function ()
{
  var chooserButtons = {};
  var volumes = [];
  var id_to_volume = {}

  function makeRow(element, volume) {
    var row = $.extend({}, volume);

    var select_widget_fn;
    var opts = element.volumeChooser('getOpts');
    if (!opts.multi_select) {
      select_widget_fn = function() {return ""};
    } else {
      console.log("checkbox element " + element.attr('id'));
      select_widget_fn = function(vol_info){return "<input type='checkbox' name='" + vol_info.id + "'/>";}
    }

    row.primary_host_name = "---"
    row.secondary_host_name = "---"
    $.each(row.volume_nodes, function(i, node) {
      if (node.primary) {
        row.primary_host_name = node.host_label
      } else if (node.use) {
        row.secondary_host_name = node.host_label
      }
    });
    row.select_widget = select_widget_fn(row);
    row.size = formatBytes(row.size);
    return row;
  }

  function getRows(element) {
    if (chooserButtons[element.attr('id')] == undefined) {
      chooserButtons[element.attr('id')] = {selected: []}
    }

    var rows = [];
    $.each(volumes, function(i, volume) {
      rows.push(makeRow(element, volume))
    });

    return rows;
  }

  function load(callback) {
    Api.get("/api/volume/", {category: 'usable', limit: 0}, success_callback = function(data) {
      volumes = data.objects;
      $.each(volumes, function(i, volume) {
        id_to_volume[volume.id] = volume;
      });
      callback();
    });
  }

  function select(element, selected) {
    var state = chooserButtons[element.attr('id')];
    if (state == undefined) {
      throw "Unknown element '#" + element.id + "'"
    }

    var old_selected = state.selected;
    if (_.isArray(selected)) {
      console.log('a');
      state.selected = selected;
    } else if (!selected) {
      state.selected = [];
    } else {
      state.selected = [selected];
    }

    // Anything in state.selected that wasn't in old_selected, cull from
    // all chooserButtons other than this one
    var newly_selected = _.difference(state.selected, old_selected);
    var no_longer_selected = _.difference(old_selected, state.selected);
    $.each(chooserButtons, function(other_element_id, other_state) {
      var other_element = $('#' + other_element_id);
      if (other_element.attr('id') == element.attr('id')) {
        return;
      }

      var dataTable = other_element.volumeChooser('getDatatable')

      _.each(newly_selected, function(remove_id) {
        $.each(dataTable.fnGetData(), function(j, row) {
          if (row.id == remove_id) {
            dataTable.fnDeleteRow(j);
          } else {
          }
        });
      });

      _.each(no_longer_selected, function(add_id) {
        dataTable.fnAddData(makeRow(other_element, id_to_volume[add_id]));
      });
    });
  }

  // When a client selects something, tell the other clients
  // to gray it out
  return {
    load: load,
    select: select,
    getRows: getRows
  }
};

(function( $ ) {
  var methods = {
    init: function(options) {
      var defaults = {
        multi_select: false,
        selected_lun_id: null,
        selected_lun_ids: []
      }

      var options = $.extend(defaults, options)

      return this.each(function() {
        fvc_button($(this), options);
      });
    },
    clear: function() {
      return this.each(function() {
        fvc_clear($(this));
      });
    },
    val: function() {
      return fvc_get_value($(this));
    },
    getDatatable: function() {
      return $(this).data('volumeChooser').data_table
    },
    getOpts: function() {
      return $(this).data('volumeChooser');
    }
  }
  $.fn.volumeChooser = function(method) {
    if ( methods[method] ) {
      return methods[ method ].apply( this, Array.prototype.slice.call( arguments, 1 ));
    } else if ( typeof method === 'object' || ! method ) {
      return methods.init.apply( this, arguments );
    } else {
      $.error( 'Method ' +  method + ' does not exist' );
    }
  };
})( jQuery );

/* fvc: Filesystem Volume Chooser */

fvc_clear = function(element) {
  opts = element.data('volumeChooser')
  element = $('#' + element.attr('id'));

  var changed;
  if (opts.multi_select) {
    if(opts['selected_lun_ids'] && opts['selected_lun_ids'].length > 0) {
      changed = true;
    }
    opts['selected_lun_ids'] = []
    opts.store.select(element, opts.selected_lun_ids)
    element.parents('.fvc_background').find('input').attr('checked', false);
  } else {
    if(opts['selected_lun_id'] != null) {
      changed = true;
    }
    opts['selected_lun_id'] = null
    opts.store.select(element, opts.selected_lun_id)
    element.parents('.fvc_background').find('.fvc_selected').html("Select storage...")
  }
  
  if (changed && opts.change) {
    opts.change();
  }
}

fvc_get_value = function(element) {
  opts = element.data('volumeChooser')
  if (opts.multi_select) {
    return opts.selected_lun_ids
  } else {
    return opts.selected_lun_id
  }
}

fvc_button = function(element, opts) {
  $('#' + element.attr('id')).data('volumeChooser', opts)

  if (!opts.store) {
    throw "'store' attribute required"
  }

  element.wrap("<div class='fvc_background'/>")
  element.hide()
  var background_div = element.parent('.fvc_background')

  element.wrap("<div class='fvc_header'/>");
  var header_div = element.parent('.fvc_header')

  element.after("<span class='fvc_selected'/>")
  var selected_label = element.next('.fvc_selected')

  header_div.after("<div class='fvc_expander'/>")
  var expander_div = header_div.next('.fvc_expander');

  if (opts.multi_select) {
    header_div.hide();
  } else {
    expander_div.hide();
  }


  header_div.button();
  /* Redoing the 'data' on the element as .button() messes with the surrounding DOM */
  element = $('#' + element.attr('id'));
  $('#' + element.attr('id')).data('volumeChooser', opts)

  // dataTables requires a unique ID
  var table_id = element.attr('id') + "_table";

  expander_div.html(
      "<table class='display tight_lines' id='" + table_id + "'>" + 
        "<thead>" +
        "  <tr>" +
        "    <th></th>" +
        "    <th></th>" +
        "    <th>Name</th>" +
        "    <th>Capacity</th>" +
        "    <th>Kind</th>" +
        "    <th>Status</th>" +
        "    <th>Primary server</th>" +
        "    <th>Failover server</th>" +
       "   </tr>" +
      "  </thead>" +
     "   <tbody>" +
    "    </tbody>" +
   "   </table>"
      );


  var table_element = expander_div.children('table')

  var volumeTable = table_element.dataTable({
    bJQueryUI: true,
    bPaginate: false,
    bInfo: false,
    bProcessing: true,
    aaData: opts.store.getRows(element),
    aoSort: [[2, 'asc']],
    aoColumns: [
      {sWidth: "1%", mDataProp: 'id', bSortable: false},
      {sWidth: "1%", mDataProp: 'select_widget', bSortable: false},
      {sWidth: "5%", mDataProp: 'label', bSortable: true},
      {sWidth: "1%", mDataProp: 'size', bSortable: false},
      {sWidth: "5%", mDataProp: 'kind', bSortable: false},
      {sWidth: "5%", mDataProp: 'status', bSortable: false},
      {sWidth: "5%", mDataProp: 'primary_host_name', bSortable: false},
      {sWidth: "5%", mDataProp: 'secondary_host_name', bSortable: false}
    ]
  });
  opts.data_table = volumeTable;

  volumeTable.fnSetColumnVis(0, false);
  if (!opts.multi_select) {
    volumeTable.fnSetColumnVis(1, false);
  }

  table_element.delegate("td", "mouseenter", function() {
    $(this).parent().children().each(function() {
      $(this).addClass('rowhighlight')
    });
  });
  table_element.delegate("td", "mouseleave", function() {
    $(this).parent().children().each(function() {
      $(this).removeClass('rowhighlight')
    });
  });

  var update_multi_select_value = function() {
    var selected = [];
    console.log(table_element);
    console.log(table_element.find('input'))
    table_element.find('input').each(function() {
      if ($(this).attr('checked')) {
        selected.push ($(this).attr('name'));
      }
    });

    opts.store.select(element, selected);
    opts.selected_lun_ids = selected
  }

  table_element.delegate("input", "click", function(event) {
    update_multi_select_value();

    event.stopPropagation();
  });

  table_element.delegate("tr", "click", function(event) {
    console.log('delegate');
    console.log(this);
    var aPos = volumeTable.fnGetPosition(this);
    var data = volumeTable.fnGetData(aPos);
    if (!opts.multi_select) {
      name = data.label;
      capacity = data.size;
      primary_server = data.primary_host_name;

      var selected_label = header_div.find('.fvc_selected')
      selected_label.html(name + " (" + capacity + ") on " + primary_server);

      opts.store.select(element, data.id);
      opts.selected_lun_id = data.id

      // TODO: a close button or something for when there are no volumes (so no 'tr')
      header_div.show();
      expander_div.slideUp();
    } else {
      var checked = $(this).find('input').attr('checked')
      $(this).find('input').attr('checked', !checked);

      update_multi_select_value();
    }

    if (opts.change) {
      opts.change();
    }
  });

  header_div.click(function() {
    header_div.hide();
    table_element.width("100%");
    
    expander_div.slideDown(null, function() {});
  });

  fvc_clear($('#' + element.attr('id')));
}

