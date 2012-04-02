
var add_host_dialog = function() {
  var template = _.template($('#add_host_dialog_template').html())
  var html = template();
  var element = $(html)
  element.dialog({title: 'Add server', resizable: false})

  element.find('.add_host_close_button').button()
  element.find('.add_host_confirm_button').button()
  element.find('.add_host_submit_button').button()
  element.find('.add_host_back_button').button()

  function select_page(name) {
    console.log(name)
    element.find('.add_host_prompt').hide();
    element.find('.add_host_loading').hide();
    element.find('.add_host_complete').hide();
    element.find('.add_host_confirm').hide();
    element.find('.add_host_error').hide();

    element.find('.' + name).show();
  }

  select_page('add_host_prompt')

  element.find('.add_host_address').keypress(function(ev) {
    if (ev.which == 13) {
      element.find('.add_host_submit_button').click();
      ev.stopPropagation();
      ev.preventDefault();
      return false;
    }
  });

  function submit_complete(result) {
      select_page('add_host_confirm')
      $('.add_host_confirm_button').focus();

      element.find('.add_host_address_label').html(result['address']);
      element.find('.add_host_resolve').toggleClass('success', result['resolve']);
      element.find('.add_host_resolve').toggleClass('failure', !result['resolve']);
      element.find('.add_host_ping').toggleClass('success', result['ping']);
      element.find('.add_host_ping').toggleClass('failure', !result['ping']);
      element.find('.add_host_agent').toggleClass('success', result['agent']);
      element.find('.add_host_agent').toggleClass('failure', !result['agent']);
  }

  function add_host_error(message) {
    select_page('add_host_error');
    element.find('.add_host_error_message').html(message);
  }

  element.find('.add_host_submit_button').click(function(ev) {
      select_page('add_host_loading')

      Api.post("test_host/", {address: element.find('.add_host_address').attr('value')},
      success_callback = function(data)
      {
         submit_complete(data);
      },
      error_callback = function(data)
      {
        //console.log(event.responseText);
        data = $.parseJSON(event.responseText);
        add_host_error(data['error']);
      });
      
      ev.preventDefault();
  });

  element.find('.add_host_confirm_button').click(function(ev) {
    Api.post("host/", {address: element.find('.add_host_address_label').html(), commit: true},
    success_callback = function(data)
    {
      select_page('add_host_complete')
      $('.add_host_back_button').focus();
      $('#server_configuration').dataTable().fnDraw();
    },
    error_callback = function(data)
    {
      add_host_error(data['errors']);
    });
    
    ev.preventDefault();
  });

  element.find('.add_host_close_button').click(function(ev) {
      element.find('.add_host_dialog').dialog('close')
      ev.preventDefault();
  });

  element.find('.add_host_back_button').click(function(ev) {
      select_page('add_host_prompt')
      ev.preventDefault();
  });
}
