//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


function add_host_dialog() {
  var template = _.template($('#add_host_dialog_template').html());
  var html = template();
  var element = $(html);
  element.dialog({title: 'Add server', resizable: false, modal: true});

  element.find('.add_host_close_button').button();
  element.find('.add_host_confirm_button').button();
  element.find('.add_host_submit_button').button();
  element.find('.add_host_back_button').button();
  element.find('.add_host_skip_button').button();

  function select_page(name) {
    element.find('.add_host_prompt').hide();
    element.find('.add_host_loading').hide();
    element.find('.add_host_complete').hide();
    element.find('.add_host_confirm').hide();

    element.find('.' + name).show();
  }

  select_page('add_host_prompt');

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

      var field_to_class = {
        resolve: 'add_host_resolve',
        ping: 'add_host_ping',
        agent: 'add_host_agent',
        reverse_ping: 'add_host_reverse_ping',
        reverse_resolve: 'add_host_reverse_resolve'};

      _.each(field_to_class, function(el_class, field) {
        element.find('.' + el_class).toggleClass('success', result[field]);
        element.find('.' + el_class).toggleClass('failure', !result[field]);
      });

      element.find('.add_host_address_label').html(result['address']);
  }

  var test_xhr;
  var test_skipped;
  element.find('.add_host_submit_button').click(function(ev) {
      select_page('add_host_loading');

      test_skipped = false;
      test_xhr = Api.post("test_host/", {address: element.find('.add_host_address').attr('value')},
      success_callback = function(data)
      {
        test_xhr = null;
        if (!test_skipped) {
          submit_complete(data);
        }
      });

      ev.preventDefault();
  });


  function create_host() {
    test_skipped = true;
    if (test_xhr) {
      test_xhr.abort();
      test_xhr = null;
    }
    Api.post("host/", {address: element.find('.add_host_address').attr('value'), commit: true},
      success_callback = function(data)
      {
        select_page('add_host_complete');
        $('.add_host_back_button').focus();
        $('#server_configuration').dataTable().fnDraw();
      });
  }

  element.find('.add_host_skip_button').click(function(ev) {
    create_host();
    ev.preventDefault();
  });

  element.find('.add_host_confirm_button').click(function(ev) {
    create_host();
    ev.preventDefault();
  });

  element.find('.add_host_close_button').click(function(ev) {
      element.dialog('close')
      element.remove();
      ev.preventDefault();
  });

  element.find('.add_host_back_button').click(function(ev) {
      select_page('add_host_prompt')
      ev.preventDefault();
  });
}
