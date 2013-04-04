//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


function add_host_dialog() {
  var template = _.template($('#add_host_dialog_template').html());
  var html = template();
  var element = $(html);
  element.dialog({title: 'Add server',
                  resizable: false,
                  modal: true,
                  width: 600,
                  close: function(){
                      $(this).remove();
                  }
                });

  element.find('.add_host_close_button').button();
  element.find('.add_host_confirm_button').button();
  element.find('.add_host_submit_button').button();
  element.find('.add_host_back_button').button();
  element.find('.add_host_skip_button').button();
  element.find('.choice_ssh_auth').buttonset();

  function select_page(name) {
    element.find('.add_host_prompt').hide();
    element.find('.add_host_loading').hide();
    element.find('.add_host_complete').hide();
    element.find('.add_host_confirm').hide();

    element.find('.' + name).show();
  }

  select_page('add_host_prompt');

  element.find('.add_host_address').keypress(function(ev) {
    if (ev.which == 13 && ! $('#id_existing_keys_choice:checked').length) {
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
        auth: 'add_host_auth',
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

      test_xhr = ValidatedForm.save(element.find('.add_host_prompt'), Api.post, "/api/test_host/", {},
          function(data) {
              if (!test_skipped) {
                  submit_complete(data);
              }
          },
          function(){
              select_page('add_host_prompt');
          });

      select_page('add_host_loading');
      element.find('.add_host_skip_button').button('enable');

      test_skipped = false;

      ev.preventDefault();
  });

  var existing_keys_div = $('#id_existing_keys');
  var root_password_div = $('#id_root_password');
  var private_key_div = $('#id_private_key');

  element.find('#id_existing_keys_choice').click(function(event){
      existing_keys_div.show();
      root_password_div.hide();
      private_key_div.hide();
  });

  element.find('#id_password_choice').click(function(event){
      existing_keys_div.hide();
      root_password_div.show();
      private_key_div.hide();

      $('#id_add_host_password').focus();
  });

  element.find('#id_other_keys_choice').click(function(event){
      existing_keys_div.hide();
      root_password_div.hide();
      private_key_div.show();

      $('#id_add_host_private_key').focus();
  });

  function create_host() {
    test_skipped = true;
    if (test_xhr) {
      test_xhr.abort();
      test_xhr = null;
    }

    //  Build params from add host dialog form elements based on checked radio
    var auth_group = $(element.find('input[type="radio"]').filter(':checked')[0]).val();
    var post_params = element
      .find('form')
      .find('div#' + auth_group)
      .find('input, textarea')
      .serializeArray()
      .reduce(function (hash, pair) {
          hash[pair.name] = pair.value;
          return hash;
      }, {commit: true});

      post_params['address'] = element
          .find('form')
          .find('#id_add_host_address').val();

      Api.post('host/', post_params,
                  success_callback = function(data)
                  {
                    select_page('add_host_complete');
                    $('.add_host_back_button').focus();
                    $('#server_configuration').dataTable().fnDraw();
                    ApiCache.put('host', data.host);
                  });
  }

  element.find('.add_host_skip_button').click(function(ev) {
    element.find('.add_host_skip_button').button('disable');
    create_host();
    ev.preventDefault();
  });

  element.find('.add_host_confirm_button').click(function(ev) {
    create_host();
    ev.preventDefault();
  });

  element.find('.add_host_close_button').click(function(ev) {
      element.dialog('close');
      ev.preventDefault();
  });

  element.find('.add_host_back_button').click(function(ev) {
      ValidatedForm.clear_errors(element);
      select_page('add_host_prompt');
      ev.preventDefault();
  });
}
