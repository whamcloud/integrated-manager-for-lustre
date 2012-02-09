
$(document).ready(function() 
{
  $("#alertAnchor").click(function()
  {
    toggleSliderDiv('alertsDiv');
    if($('#alertsDiv').css('display') == 'block')
    {
      $('div.leftpanel table#alerts').dataTable().fnDraw();
    }
  });
  
  $("#eventsAnchor").click(function()
  {
    toggleSliderDiv('eventsDiv')
    if($('#eventsDiv').css('display') == 'block')
    {
      $('div.leftpanel table#events').dataTable().fnDraw();
    }
  });
  
  $("#jobsAnchor").click(function()
  {
    toggleSliderDiv('jobsDiv');
    if($('#jobsDiv').css('display') == 'block')
    {
      $('div.leftpanel table#jobs').dataTable().fnDraw();
    }
  });
  
  $("#minusImg").click(function()
  {
   $("#frmsignin").toggle("slow");
   $("#signbtn").toggle("slow");
   return false;
  });
});

eventStyle = function(ev)
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

eventIcon = function(e)
{
  return "/static/images/" + {
    INFO: 'dialog-information.png',
    ERROR: 'dialog-error.png',
    WARNING: 'dialog-warning.png',
  }[e.severity]
}

toggleSliderDiv = function(divname)
{
  var slider_divs =['alertsDiv','eventsDiv','jobsDiv'];
  for (var i = 0 ;i < slider_divs.length ; i++)
  { 
    if (slider_divs[i] == divname)
    {
      if($("#"+divname).css("display") == "none")
      {
        $("#"+divname).css("display","block");
      }
      else
      {
        $("#"+divname).css("display","none");
      }    
    }
    else
    {
      $("#"+slider_divs[i]).hide();
    }
  }
}

function jobIcon(job)
{
  var prefix = "/static/images/";
  if(job.state == 'complete') {
    if (job.errored) {
      return prefix + "dialog-error.png"
    } else if (job.cancelled) {
      return prefix + "gtk-cancel.png"
    } else {
      return prefix + "dialog_correct.png"
    }
  } else if (job.state == 'paused') {
    return prefix + "gtk-media-pause.png"
  } else {
    return prefix + "ajax-loader.gif"
  }
}

function alertIcon(a)
{
  return "/static/images/dialog-warning.png";
}

setJobState = function(job_id, state)
{
  Api.put("job/" + job_id + "/", {'state': state},
  success_callback = function(data)
  {
    $('div.leftpanel table#jobs').dataTable().fnDraw();
  });
}

/* FIXME: move this somewhere sensible */
loadHostList = function(filesystem_id, targetContainer)
{
  var hostList = '<option value="">All</option>';
  
  var api_params = {'filesystem_id':filesystem_id};

  Api.get("host/", api_params,
  success_callback = function(data)
  {
    $.each(data.objects, function(i, host)
    {
      hostList  =  hostList + "<option value="+host.id+">"+host.label+"</option>";
    });
    $('#'+targetContainer).html(hostList);
  });
}

setActiveMenu = function(menu_element){
  $('#'+menu_element).addClass('active');
}

$(document).ready(function() {
  smallTable($('div.leftpanel table#jobs'), 'job/',
    {},
    function(job) {
      job.icon = "<img src='" + jobIcon(job) + "'/>"
      job.buttons = ""
      $.each(job.available_transitions, function(i, transition) {
        /* TODO: use job URL */
        /* FIXME: relying on global function */
        job.buttons += "<input type='button' class='ui-button ui-state-default ui-corner-all ui-button-text-only notification_job_buttons' onclick=setJobState("+job.id+",'"+transition.state+"') value="+transition.label+" />";
      });
    },
    [
      { "sClass": 'txtleft', "mDataProp":"icon" },
      { "sClass": 'txtleft', "mDataProp":"description" },
      { "sClass": 'txtleft', "mDataProp":"buttons" },
      { "sClass": 'txtleft', "mDataProp":"created_at" }
    ]
  );

  smallTable($('div.leftpanel table#alerts'), 'alert/',
    {active: true},
    function(a) {
      a.icon = "<img src='" + alertIcon(a) + "'/>"
    },
    [
      { "sClass": 'txtleft', "mDataProp":"icon" },
      { "sClass": 'txtleft', "mDataProp":"message" },
      { "sClass": 'txtleft', "mDataProp":"begin" },
    ]
  );

  smallTable($('div.leftpanel table#events'), 'event/',
    {},
    function(e) {
      e.icon = "<img src='" + eventIcon(e) + "'/>"
      if (!e.host) {
        e.host_name = "";
      }
      e.DT_RowClass = eventStyle(e)
    },
    [
      { "sClass": 'txtleft', "mDataProp": "icon" },
      { "sClass": 'txtleft', "mDataProp": "host_name" },
      { "sClass": 'txtleft', "mDataProp": "message" },
      { "sClass": 'txtleft', "mDataProp": "created_at" },
    ]
  );

  function smallTable(element, url, kwargs, row_fn, columns) {
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
          "sProcessing": "<img src='/static/images/loading.gif' style='margin-top:10px;margin-bottom:10px' width='16' height='16' />"
        },
        bJQueryUI: true,
        bFilter: false
      });
    // Hide the header
    element.prev().hide();
    element.find('thead').hide();
  }
});
