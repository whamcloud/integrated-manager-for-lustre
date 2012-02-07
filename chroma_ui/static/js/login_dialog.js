
$(document).ready(function() {
  $('#user_info #authenticated').hide();
  $('#user_info #anonymous').show();
  invoke_api_call(api_get, "session/", {}, success_callback = function(session) {
    var user = session.user
    if (!user) {
      $('#user_info #authenticated').hide();
      $('#user_info #anonymous').show();
    } else {
      $('#user_info #authenticated #username').html(user.username)
      $('#user_info #authenticated').show();
      $('#user_info #anonymous').hide();
    }
  });

  $('#user_info #authenticated #logout').click(function(event) {
    invoke_api_call(api_delete, "session/", {}, success_callback = function() {
      window.location.href = "/ui/";
    });
    event.preventDefault();
  });

  $('#user_info #anonymous #login').click(function(event) {
    $('#login_dialog #error').hide()
    $('#login_dialog input[name=username]').val("")
    $('#login_dialog input[name=password]').val("")
    $('#login_dialog').dialog('open');
    $("#login_dialog input[name=username]").focus();
    event.preventDefault();
  });

  $("#login_dialog input[name=username]").keyup(function(event){
    if(event.keyCode == 13){
      $("#login_dialog input[name=password]").focus();
    }
  });

  $("#login_dialog input[name=password]").keyup(function(event){
    if(event.keyCode == 13){
      login_dialog_submit();
    }
  });

  var login_dialog_submit = function() {
    var username = $('#login_dialog input[name=username]').val()
    var password = $('#login_dialog input[name=password]').val()
    invoke_api_call(api_post, 'session/', {username: username, password: password},
      success_callback = function() {
        window.location.href = "/ui/";
      },
      error_callback = {403: function(status, jqXHR) {
        $('#login_dialog #error').show()
        $("#login_dialog input[name=username]").focus();
      }}
    );
  }

  $('#login_dialog').dialog({
    autoOpen: false,
    modal: true,
    title: "Login",
    resizable: false});
  $('#login_dialog').dialog('option', 'buttons', {
    'Cancel': function() {$(this).dialog('close')},
    'Login': login_dialog_submit
  });

});
