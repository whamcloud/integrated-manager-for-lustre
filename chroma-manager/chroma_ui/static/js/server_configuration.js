//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


function add_host_dialog(serverProfile) {
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
  element.find('.add_host_revalidate_button').button();
  element.find('.add_host_https_generate_button').button();
  element.find('.add_host_https_back_button').button();
  element.find('.choice_ssh_auth').buttonset();

  var $https_server_profile = element.find('div.add_host_https select.add_server_profile');

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
        hostname_valid: 'add_host_hostname_valid',
        fqdn_resolves: 'add_host_fqdn_resolves',
        fqdn_matches: 'add_host_fqdn_matches',
        reverse_ping: 'add_host_reverse_ping',
        reverse_resolve: 'add_host_reverse_resolve',
        yum_valid_repos: 'add_host_yum_valid_repos',
        yum_can_update: 'add_host_yum_can_update'
      };

      _.each(field_to_class, function(el_class, field) {
        element.find('.' + el_class).toggleClass('success', result[field]);
        element.find('.' + el_class).toggleClass('failure', !result[field]);
      });

      var failed_tests = Object.keys(field_to_class).filter(function (field) { return !result[field]; });

      element.find('.add_host_confirm_override_prompt').css(failed_tests.length > 0 ? {"visibility": "visible", "display": "block"} : {"visibility": "hidden", "display": "none"});
      element.find('.add_host_confirm_button').button('option', 'disabled', failed_tests.length > 0);
      element.find('#id_failed_validations').val(failed_tests.join());
      element.find('.add_host_address_label').html(result['address']);
  }

  var test_xhr;
  var test_skipped;

  function gatherParams() {
      var $form = element.find('form');
      var auth_group = $($form.find('div.choice_ssh_auth input[type="radio"]').filter(':checked')[0]).val();
      var form_params = $form
          .find('div#' + auth_group)
          .find('input, textarea, select')
          .add('#id_add_host_address, select.add_server_profile, #id_failed_validations')
          .serializeArray()
          .reduce(function (hash, pair) {
            if (pair.value.trim().length > 0)
              hash[pair.name] = pair.value;

            return hash;
          }, {commit: true, auth_type: auth_group});
      return form_params;
  }
  element.find('.add_host_submit_button').click(function(ev) {
      var form_params = gatherParams();
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

  var existing_keys_div = $('#existing_keys_choice');
  var root_password_div = $('#id_password_root');
  var private_key_div = $('#private_key_choice');

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
    Api.get("server_profile/?order_by=default&order_by=-managed", {limit: 0}, success_callback = function(data) {
      var $select = $('div.add_host_dialog select[name="server_profile"]');

      //unshift an empty option into the objects.
      data.objects.unshift({
        resource_uri: undefined,
        ui_name: '---'
      });

      data.objects.forEach(function(profile) {

        var option = '<option value="%s"%s>%s</option>'.sprintf(
          (profile.resource_uri == null ? '': profile.resource_uri),
          (profile.resource_uri === serverProfile() ? 'selected="selected"' : ''),
          profile.ui_name
        );

        $select.append(option);
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
    var post_params = gatherParams();

    serverProfile(post_params.server_profile);
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
        profile: $https_server_profile.val(),
        expiry: XDate(true).addMinutes($slider_expiry.slider('value')).toISOString()  //$slider_expiry.slider('value') * 60
      },
      success_callback = function(token) {
        var limit_string = 'This command can be used for %d storage server%s until %s.'.sprintf(
          token.credits,
          ( token.credits > 1 ? 's' : '' ),
          XDate( token.expiry ).toString()
        );
        $generate_button.button('enable');
        element.find('.add_host_https_command pre').text(token.register_command);
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

  element.find('.add_host_confirm_override_button').click(function(ev) {
    element.find('.add_host_confirm_button').button('enable');
  });

  element.find('.add_host_close_button').click(function(ev) {
      element.dialog('close');
      ev.preventDefault();
  });

  element.find('.add_host_revalidate_button').click(function(ev) {
    element.find('.add_host_submit_button').click();
    ev.preventDefault();
  });

  element.find('.add_host_back_button').click(function(ev) {
      ValidatedForm.clear_errors(element);
      select_page('.add_host_prompt', ssh_pages);
      ev.preventDefault();
  });
}
