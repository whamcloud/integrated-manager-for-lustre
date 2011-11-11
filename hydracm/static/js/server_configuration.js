
var add_host_dialog = function() {
  $('#add_host_tabs').tabs('select', '#add_host_prompt');
  $('#add_host_dialog').dialog('open');
  $('#add_host_address').focus();
}

$(document).ready(function() {
  /* FIXME: HYD-439 this code is getting re-run each time the 
   * user navigates to the server configuration tab, resulting
   * in multiple signal handlers for e.g. adding the host */
  $('#add_host_dialog').dialog({
      autoOpen: false,
      title: "Add server",
      resizable: false
  });
  $('#add_host_tabs').tabs()

  $('.add_host_close_button').button()
  $('.add_host_confirm_button').button()
  $('.add_host_submit_button').button()
  $('.add_host_back_button').button()

  $('#add_host_address').keypress(function(ev) {
      if (ev.which == 13) {
          $('.add_host_submit_button').click();
          ev.stopPropagation();
          ev.preventDefault();
          return false;
      }
  });
  function submit_complete(result) {
      console.log('submit_complete: ' + result);
      $('#add_host_tabs').tabs('select', '#add_host_confirm');
      $('.add_host_confirm_button').focus();

      $('#add_host_address_label').html(result['address']);
      $('#add_host_resolve').toggleClass('success', result['resolve']);
      $('#add_host_resolve').toggleClass('failure', !result['resolve']);
      $('#add_host_ping').toggleClass('success', result['ping']);
      $('#add_host_ping').toggleClass('failure', !result['ping']);
      $('#add_host_agent').toggleClass('success', result['agent']);
      $('#add_host_agent').toggleClass('failure', !result['agent']);
  }

  function add_host_error(message) {
      $('#add_host_tabs').tabs('select', '#add_host_error');
      $('#add_host_error_message').html(message);
  }

  function submit_poll(task_id) {
      $.get('/djcelery/' + task_id + '/status/')
          .success(function(data, textStatus, jqXHR) {
              task_status = data['task']['status']
              console.log(task_status)
              if (task_status == 'SUCCESS') {
                  console.log(data);
                  submit_complete(data['task']['result']);
              } else if (task_status == 'FAILURE') {
                  console.log(event.responseText);
                  add_host_error("Internal error.");
              } else {
                  /* Incomplete, schedule re-check */
                  setTimeout(function() {submit_poll(task_id)}, 1000);
              }
              })
          .error(function(event) {
                  console.log(event.responseText);
                  add_host_error("Failed to get status for task " + task_id + ".");
              });
  }

  $('.add_host_submit_button').click(function(ev) {
      $('#add_host_tabs').tabs('select', '#add_host_loading');

      $.post('/api/test_host/', {hostname: $('#add_host_address').attr('value'), commit: false})
      .success(function(data, textStatus, jqXHR) {
          task_id = data.response.task_id
          submit_poll(task_id) 
      })
      .error(function(event) {
          console.log(event.responseText);
          data = $.parseJSON(event.responseText);
          add_host_error(data['error']);
      });
      ev.preventDefault();
  });

  $('.add_host_confirm_button').click(function(ev) {
          $.post('/api/add_host/', {hostname: $('#add_host_address_label').html(), commit: true})
      .success(function(data, textStatus, jqXHR) {
          $('#add_host_tabs').tabs('select', '#add_host_complete');
          $('.add_host_back_button').focus();
          $('#server_configuration').dataTable().fnClearTable();
          LoadServerConf_ServerConfig();
      })
      .error(function(event) {
          console.log(event.responseText);
          add_host_error(data['error'])
      });

      ev.preventDefault();
  });

  $('.add_host_close_button').click(function(ev) {
      $('#add_host_dialog').dialog('close')
      ev.preventDefault();
  });

  $('.add_host_back_button').click(function(ev) {
      $('#add_host_tabs').tabs('select', '#add_host_prompt')
      ev.preventDefault();
  });
});
