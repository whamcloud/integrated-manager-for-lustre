
$(document).ready(function() {
  Login.init();
});

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
        window.location.href = "/ui/";
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
        window.location.href = "/ui/";
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

        Api.enable();

        $('.fsadmin_only').toggle(userHasGroup('filesystem_administrators'));
        $('.superuser_only').toggle(userHasGroup(user, 'superusers'));
      }
    }, undefined, false, true);
  }

  function getUser(){
    return user;
  }

  return {
    init: init,
    getUser: getUser
  }
}();
