//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var Login = function() {
  var user = null;

  function userHasGroup(required_group) {
    if (!user) {
      return false;
    } else {
      var match = false;
      for(var i = 0; i < user.groups.length; i++) {
        group = user.groups[i];
        if ((group.name == required_group) || (group.name == "superusers")) {
          return true;
        }
      }
      return false;
    }
  }

  function open() {
    $('#login_dialog').prev().find('.ui-dialog-titlebar-close').hide()
    $('#login_dialog #error').hide()
    $('#login_dialog input[name=username]').val("")
    $('#login_dialog input[name=password]').val("")
    $('#login_dialog').dialog('open');
    $("#login_dialog input[name=username]").focus();
  }

  function submit() {
    var username = $('#login_dialog input[name=username]').val()
    var password = $('#login_dialog input[name=password]').val()
    Api.post('session/', {username: username, password: password},
      success_callback = function() {
        window.location.href = Api.UI_ROOT;
      },
      error_callback = {403: function(status, jqXHR) {
        $('#login_dialog #error').show()
        $("#login_dialog input[name=username]").focus();
      }},
      true, true
    );
  }

  function initUi() {
    $('#user_info #authenticated').hide();
    $('#user_info #anonymous').show();

    $('#user_info #authenticated #logout').click(function(event) {
      Api.delete("session/", {}, success_callback = function() {
        window.location.href = Api.UI_ROOT;
      });
      event.preventDefault();
    });

    $('#user_info #anonymous #login').click(function(event) {
      open();
      event.preventDefault();
    });

    $("#login_dialog input[name=username]").keyup(function(event){
      if(event.keyCode == 13){
        $("#login_dialog input[name=password]").focus();
      }
    });

    $("#login_dialog input[name=password]").keyup(function(event){
      if(event.keyCode == 13){
        submit();
      }
    });

    $('#login_dialog').dialog({
      autoOpen: false,
      modal: true,
      title: "Login",
      draggable: false,
      resizable: false,
      buttons: {
        'Cancel': function() {$('#login_dialog').dialog('close')},
        'Login': submit
      }
    });
    $('#login_dialog + div button:first').attr('id', 'cancel');
    $('#login_dialog + div button:last').attr('id', 'submit');

    $('#user_info #authenticated #account').click(function(ev)
    {
      Backbone.history.navigate("/user/" + Login.getUser().id + "/", true);
      ev.preventDefault();
    })
  }

  function init() {
    initUi();

    /* Discover information about the currently logged in user (if any)
     * so that we can put the user interface in the right state and 
     * enable API calls */
    Api.get("/api/session/", {}, success_callback = function(session) {
      user = session.user
      $('.read_enabled_only').toggle(session.read_enabled);

      if (!session.read_enabled) {
        /* User can do nothing until they log in */
        open();
        $('#login_dialog').next().find('button:first').hide()
      } else {
        if (!user) {
          $('#user_info #authenticated').hide();
          $('#user_info #anonymous').show();
        } else {
          $('#user_info #authenticated #username').html(user.username)
          $('#user_info #authenticated').show();
          $('#user_info #anonymous').hide();
        }

        $('.fsadmin_only').toggle(userHasGroup('filesystem_administrators'));
        $('.superuser_only').toggle(userHasGroup(user, 'superusers'));

        Api.enable();
      }
    }, undefined, false, true);
  }

  function getUser(){
    return user;
  }

  return {
    init: init,
    getUser: getUser,
    userHasGroup: userHasGroup
  }
}();

var ValidatedForm = function() {
  function add_error(input, message) {
    input.before("<span class='error'>" + message + "</span>");
    input.addClass('error');
  }

  function save(element, api_fn, url, obj, success, error) {
    element.find('input').each(function() {
      obj[$(this).attr('name')] = $(this).val()
    });
    return api_fn(url, obj,
      success_callback = function(data) {
        if (success) {
          success(data);
        }
      },
      {
        400: function(jqXHR) {
          if (error) {
            error();
          }
          var errors = JSON.parse(jqXHR.responseText);
          element.find('span.error').remove();
          element.find('input').removeClass('error');
          $.each(errors, function(attr_name, error_list) {
            $.each(error_list, function(i, error) {
              add_error(element.find('input[name=' + attr_name + ']'), error);

            });
          });
        }
      }
    );
  }

  function clear_errors(element) {
    element.find('span.error').remove();
    element.find('input').removeClass('error');
  }

  function clear(element) {
    element.find('input').val("");
    clear_errors(element);
  }

  function reset(element, obj) {
    element.find('input').each(function() {
      $(this).val(obj.get($(this).attr('name')));
    });
  }

  return {
    add_error: add_error,
    save: save,
    clear: clear,
    reset: reset,
    clear_errors: clear_errors
  }
}();
