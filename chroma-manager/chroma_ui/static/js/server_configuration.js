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


function add_host_dialog() {

  /* Dialog setup */
  var template = _.template($('#add_host_dialog_template').html());
  var element;

  // slider settings
  var credits = {
    default: 1,
    min: 1,
    max: 128,
    step: 1,
    text_renderer: function(ev, ui) {
      var value = (ui && ui.value) ? ui.value : credits.default;
      element.find('.text-credits').text(value);
    }
  };

  var expiry = {
    default: 5,
    min: 5,
    max: 600, // 10 hours
    step: 5,
    text_formatter: function(value) {
      var hours = Math.floor(value / 60);
      var minutes = value - (hours * 60 );
      return ( hours > 0 ? hours + 'h' : '') + ( minutes > 0 ? minutes + 'm' : '');
    },
    text_renderer: function(ev,ui) {
      var value = ui.value ? ui.value : expiry.default;
      element.find('.text-expiry').text( expiry.text_formatter(value) );
    }
  };

  // Triggers re-centering of dialog, use after dynamic data changes
  function center_dialog() {
    element.dialog('option','position', { my: 'center top', at: 'center top', offset: '0 50'} );
  };

  $(window).resize(center_dialog);

  element = $(template({ credits: credits, expiry: expiry }));
  element.dialog({title: 'Add server',
                  resizable: false,
                  modal: true,
                  width: 'auto',
                  close: function(){
                      $(this).remove();
                      $(window).unbind('resize',center_dialog);
                  }
                });

  get_profiles();

  element.find('.add_host_close_button').button();
  element.find('.add_host_confirm_button').button();
  element.find('.add_host_submit_button').button();
  element.find('.add_host_back_button').button();
  element.find('.add_host_skip_button').button();
  element.find('.add_host_ssh_button').button();
  element.find('.add_host_https_generate_button').button();
  element.find('.add_host_https_back_button').button();
  element.find('.choice_ssh_auth').buttonset();

  var $slider_credits = element.find('.slider-credits');
  $slider_credits.slider({
    value:  credits.default,
    max:    credits.max,
    min:    credits.min,
    step:   credits.step,
    slide:  credits.text_renderer,
    create: credits.text_renderer
  });

  var $slider_expiry = element.find('.slider-expiry');
  $slider_expiry.slider({
    value:  expiry.default,
    max:    expiry.max,
    min:    expiry.min,
    step:   expiry.step,
    slide:  expiry.text_renderer,
    create: expiry.text_renderer
  });

  // future-proof tab behaviour by using show (jqueryui 1.8.x) and activate (1.10.x)
  element.find('.add_host_wizard').tabs({ show: center_dialog, activate: center_dialog});

  var ssh_pages = ['.add_host_prompt','.add_host_loading','.add_host_complete','.add_host_confirm'];
  var https_pages = ['.add_host_https','.add_host_https_command'];

  function select_page(show_page,pages) {
    element.find(pages.join(',')).hide();
    element.find(show_page).show();
    center_dialog();
  }

  select_page('.add_host_prompt', ssh_pages);
  select_page('.add_host_https', https_pages);

  element.find('.add_host_address').keypress(function(ev) {
    if (ev.which == 13 && element.find('#id_existing_keys_choice:checked').length) {
      element.find('.add_host_submit_button').click();
      ev.stopPropagation();
      ev.preventDefault();
      return false;
    }
  });

  function submit_complete(result) {
      select_page('.add_host_confirm', ssh_pages)
      $('.add_host_confirm_button').focus();

      var field_to_class = {
        resolve: 'add_host_resolve',
        ping: 'add_host_ping',
        auth: 'add_host_auth',
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

      var form_params = element
          .find('form').find('input, textarea, select')
          .filter(':visible')
          .serializeArray()
          .reduce(function (hash, pair) {
              hash[pair.name] = pair.value;
              return hash;
          }, {commit: true});

      test_xhr = ValidatedForm.save(element.find('.add_host_prompt'), Api.post, "/api/test_host/", {},
          function(data) {
              if (!test_skipped) {
                  submit_complete(data);
              }
          },
          function(){
              select_page('.add_host_prompt', ssh_pages);
          },
          form_params);

      select_page('.add_host_loading', ssh_pages);
      element.find('.add_host_skip_button').button('enable');

      test_skipped = false;

      ev.preventDefault();
  })

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

  function get_profiles() {
    Api.get("profile/", {limit: 0}, success_callback = function(data) {
      $.each(data.objects, function(i, profile) {
        var option = "<option value='" + profile.name + "'>"+ profile.ui_name + "</option>";
        $('div.add_host_dialog select[name=\'profile\']').prepend(option)
      });
    });
  }

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
      .find('input, textarea, select')
      .serializeArray()
      .reduce(function (hash, pair) {
          hash[pair.name] = pair.value;
          return hash;
      }, {commit: true});

      post_params['address'] = element
          .find('form')
          .find('#id_add_host_address').val();

      post_params['profile'] = element
          .find('form')
          .find('.add_server_profile').val();

      Api.post('host/', post_params,
                  success_callback = function(data)
                  {
                    select_page('.add_host_complete', ssh_pages);
                    $('.add_host_back_button').focus();
                    $('#server_configuration').dataTable().fnDraw();
                    ApiCache.put('host', data.host);
                  });
  }

  /* HTTPS buttons */
  element.find('.add_host_https_button').click(function(ev) {
    element.find('.add_host_https_generate_button').button('enable');
    element.find('.https_command_container').hide();
    select_page('.add_host_https', https_pages);
    ev.preventDefault();
  });

  element.find('.add_host_https_generate_button').click(function(ev) {
    var $generate_button = $(this);
    $generate_button.button('disable');
    // gather data
    Api.post('registration_token/',
      {
        credits: $slider_credits.slider('value'),
        expiry: XDate(true).addMinutes($slider_expiry.slider('value')).toISOString()  //$slider_expiry.slider('value') * 60
      },
      success_callback = function(token) {

        var command_line = 'curl -k %s//%s/agent/setup/%s/ | python'.sprintf(
          window.location.protocol,
          window.location.host,
          token.secret
        );
        var limit_string = 'This command can be used for %d storage server%s until %s.'.sprintf(
          token.credits,
          ( token.credits > 1 ? 's' : '' ),
          XDate( token.expiry ).toString()
        );
        $generate_button.button('enable');
        element.find('.add_host_https_command pre').text(command_line);
        element.find('.add_host_https_command p.token_limits').text(limit_string);
        select_page('.add_host_https_command', https_pages);
      },
      error_callback = undefined,
      blocking = false
    )
    //api call
      //succes callback
    ev.preventDefault();
  });

  element.find('.add_host_https_back_button').click(function(ev){
    select_page('.add_host_https', https_pages);
    ev.preventDefault();
  });

  /* SSH Buttons */
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
      select_page('.add_host_prompt', ssh_pages);
      ev.preventDefault();
  });
}
