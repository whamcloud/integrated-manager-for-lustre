
/* fvc: Filesystem Volume Chooser */

var fvc_instances = []

fvc_get_value = function(element) {
  opts = fvc_instances[element.attr('id')]
  console.log(opts);
  if (opts.multi_select) {
    return opts.selected_lun_ids
  } else {
    return opts.selected_lun_id
  }
}

fvc_button = function(element, opts) {
  if (!opts) {
    opts = []
  }
  if (opts.multi_select) {
    opts['selected_lun_ids'] = []
  } else {
    opts['selected_lun_id'] = null
  }

  fvc_instances[element.attr('id')] = opts

  element.wrap("<div class='fvc_background'/>")
  element.hide()

  element.wrap("<div class='fvc_header'/>")
  var header_div = element.parent('.fvc_header')

  element.after("<span class='fvc_selected'/>")
  var selected_label = element.next('.fvc_selected')
  selected_label.html("None selected")


  header_div.after("<div class='fvc_expander'/>")
  var expander_div = header_div.next('.fvc_expander');
  expander_div.css('width', '100%');
  expander_div.css('height', '300px');

  if (opts.multi_select) {
    header_div.hide();
  } else {
    expander_div.hide();
  }

  /* dataTables requires a unique ID */
  var table_id = element.attr('id') + "_table";

  expander_div.html(
      "<table id='" + table_id + "'>" + 
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
    bProcessing: true
  });

  volumeTable.fnSetColumnVis(0, false);
  if (!opts.multi_select) {
    volumeTable.fnSetColumnVis(1, false);
  }

  if (!opts.multi_select) { 
    LoadUsableVolumeList(table_element, function() {return ""});
  } else {
    LoadUsableVolumeList(table_element, function(vol_info){return "<input type='checkbox' name='" + vol_info.id + "'/>";});
  }

  /*element.next('.fvc_expander').children('table').dataTable().fnClearTable();*/

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

  table_element.delegate("tr", "click", function() {
    var aPos = volumeTable.fnGetPosition(this);
    var data = volumeTable.fnGetData(aPos);
    if (!opts.multi_select) {
      console.log("single select");
      name = data[2];
      capacity = data[3];
      primary_server = data[6];
      failover_server = data[7];

      var selected_label = header_div.find('.fvc_selected')
      selected_label.html(name + " (" + capacity + ") on " + primary_server);
      console.log(name + " (" + capacity + ") on " + primary_server);


      fvc_instances[element.attr('id')].selected_lun_id = data[0]

      /* TODO: a close button or something for when there are no volumes (so no 'tr') */
      /*element.attr('disabled', false)*/
      header_div.show();
      expander_div.slideUp();
    } else {
      console.log("multi select");
      var checked = $(this).find('input').attr('checked')
      $(this).find('input').attr('checked', !checked);

      /* TODO also do this on actually clicking the checkbox */
      var selected = [];
      var checkboxes = table_element.find('input').each(function() {
        if ($(this).attr('checked')) {
          selected.push ($(this).attr('name'));
        }
      });

      fvc_instances[element.attr('id')].selected_lun_ids = selected
    }
  });

  header_div.button();
  header_div.click(function() {
    /*element.attr('disabled', true)*/
    header_div.hide();
    expander_div.slideDown();
  });
}

