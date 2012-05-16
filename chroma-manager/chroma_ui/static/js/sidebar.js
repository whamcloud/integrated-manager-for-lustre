//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================




var Sidebar = function(){
  var initialized = false;

  function eventStyle(ev)
  {
    var cssClassName = "";
    if(ev.severity == 'ERROR') //red
      cssClassName='palered';
    else if(ev.severity == 'INFO') //normal
      cssClassName='';
    else if(ev.severity == 'WARNING') //yellow
      cssClassName='brightyellow';
    
    return cssClassName;
  }

  function eventIcon(e)
  {
    return "/static/images/" + {
      INFO: 'fugue/information.png',
      ERROR: 'fugue/exclamation-red.png',
      WARNING: 'fugue/exclamation.png'
    }[e.severity]
  }

  var job_icon_template = _.template($('#job_icon_template').html());

  function commandIcon(command)
  {
    var prefix = "/static/images/";
    if(!command.complete) {
      return prefix + "loading.gif"
    } else if (command.errored) {
        return prefix + "fugue/exclamation-red.png"
    } else if (command.cancelled) {
        return prefix + "fugue/cross-white.png"
    } else {
        return prefix + "fugue/tick.png"
    }
  }

  function alertIcon(a)
  {
    return "/static/images/fugue/exclamation-red.png";
  }

  function dismissIcon(a) {
    if (a.dismissed === true) {
      return '';
    }
    else {
      return "<img alt='Dismiss' class='dismiss_button' title='Dismiss' src='/static/images/fugue/tick.png' />";
    }
  }

  function ellipsize(str)
  {
    /* FIXME: find or implement real ellipsization by element size
     * rather than arbitrary string length limit */
    var length = 40;
    if (str.length > (length - 3)) {
      return str.substr(0, length) + "..."
    } else {
      return str
    }
  }

  function refresh() {
    var active = $('div#sidebar div#accordion').accordion("option", "active");
    if (active == false) {
      /* pass */
    } else if (active == 0) {
      $('div.leftpanel table#alerts').dataTable().fnDraw();
    } else if (active == 1) {
      $('div.leftpanel table#events').dataTable().fnDraw();
    } else if (active == 2) {
      $('div.leftpanel table.commands').dataTable().fnDraw();
    } else {
      throw "Unknown accordion index " + active
    }
  }

  function init() {
    $("div#sidebar div#accordion").accordion({
      fillSpace: true,
      collapsible: true,
      changestart: function (event, ui) {
        refresh();
      }
    });

    smallTable($('div.leftpanel table.commands'), 'command/',
      {order_by: "-created_at"},
      function(command) {
        command.icon = "<img src='" + commandIcon(command) + "'/>"
        // TODO: cancelling jobs within commands (and commands themselves?)
        command.text = ellipsize(command.message) + "<br>" + shortLocalTime(command.created_at)
        command.buttons = "<a class='navigation' href='/command/" + command.id + "/'>Open</a>";
      },
      [
        { "sClass": 'icon_column', "mDataProp":"icon", bSortable: false },
        { "sClass": 'txtleft', "mDataProp":"text", bSortable: false },
        { "sClass": 'txtleft', 'mDataProp': 'buttons', bSortable: false }
      ]
    );

    smallTable($('div.leftpanel table#alerts'), 'alert/',
      {active: true, order_by: "-begin"},
      function(a) {
        a.text = ellipsize(a.message) + "<br>" + shortLocalTime(a.begin);
        a.icon = "<img src='" + alertIcon(a) + "'/>";
        a.dismiss = dismissIcon(a);
      },
      [
        { "sClass": 'icon_column', "mDataProp":"icon", bSortable: false },
        { "sClass": 'txtleft', "mDataProp":"text", bSortable: false },
        { "sClass": 'dismiss_column', "mDataProp":"dismiss", bSortable: false }
      ],
      "<img src='/static/images/fugue/tick.png'/>&nbsp;No alerts active"
    );
    
    // delegated event for dismissing an alert
    $("#alerts").delegate("img.dismiss_button", "click", function() {
      var dismiss_icon = this;
      
      // get the stored alert data, set to dismissed
      var dataTable = $('div.leftpanel table#alerts').dataTable()
      var alert_info = dataTable.fnGetData($(dismiss_icon).closest('tr').get(0));
      alert_info.dismissed = true;
      Api.put(
        'alert/' + alert_info.id + '/',
        api_params = alert_info,
        // remove the dismiss image, deactivate the alert
        success_callback = function() {
          $(dismiss_icon).parents('tr:eq(0)').removeClass('odd even').addClass('alert_row_dismissed');
          $(dismiss_icon).remove();
          AlertNotification.deactivateAlert(alert_info);
        },
        error_callback = undefined,
        blocking = false
      );

    });

    smallTable($('div.leftpanel table#events'), 'event/',
      {order_by: "-created_at"},
      function(e) {
        e.icon = "<img src='" + eventIcon(e) + "'/>"
        e.DT_RowClass = eventStyle(e)
        e.text = ellipsize(e.message) + "<br>" + shortLocalTime(e.created_at)
      },
      [
        { "sClass": 'icon_column', "mDataProp": "icon", bSortable: false },
        { "sClass": 'txtleft', "mDataProp": "text", bSortable: false },
      ]
    );

    initialized = true;
  }

  function smallTable(element, url, kwargs, row_fn, columns, emptyText) {
    element.dataTable({
        bProcessing: true,
        bServerSide: true,
        iDisplayLength:10,
        bDeferRender: true,
        sAjaxSource: url,
        fnServerData: function (url, data, callback, settings) {
          Api.get_datatables(url, data, function(data){
            $.each(data.aaData, function(i, row) {
              row_fn(row);
            });
            callback(data);
          }, settings, kwargs);
        },
        aoColumns: columns,
        oLanguage: {
          "sProcessing": "<img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' />",
          sZeroRecords: emptyText
        },
        bJQueryUI: true,
        bFilter: false
      });
    // Hide the header
    element.prev().hide();
    element.find('thead').hide();

    // Hide the "x of y" text from the footer
    element.next().find('.dataTables_info').hide();
  }

  function open() {
    if (!initialized) {
      init();
    }

    refresh();
    $("#sidebar").show({effect: 'slide'});
  }

  function close() {
    $("#sidebar").hide({effect: 'slide'});
  }

  return {
    open: open,
    close: close
  }
}();




$(document).ready(function() 
{
  $("#sidebar_open").click(function()
  {
    Sidebar.open();
    return false;
  });

  $("#sidebar_close").button({icons:{primary:'ui-icon-close'}});
  $("#sidebar_close").click(function()
  {
    Sidebar.close();
    return false;
  });
});


