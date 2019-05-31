function updateCrawlerInfo(info){
    $('#connection-count').val(info['connection-count']);
    $('#crawler-count').val(info['crawler-count']);
    $('#crawler-num').val(info['crawler-count']);
    $('#spider-count').val(info['spider-count']);
    $('#active-count').val(info['active-count']);
    $('#task-count').val(info['task-count']);
}

$(document).ready(() => {
    let nav = getNav();
    if (nav['status'] === 0)
        nav = nav['data'];
    else
        $.notify({
            type: 'danger',
            message: nav['msg']
        });

    let currentHostPort = window.location.hostname + ':' + window.location.port;
    let websocket = new WebSocket('ws://' + currentHostPort + nav['websocket_url']);
    websocket.onmessage = (data) => {
      let jsonData = JSON.parse(data.data);

      if ('crawler_info' in jsonData)
          updateCrawlerInfo(jsonData['crawler_info']);
      if ('message' in jsonData)
        $.notify({
            icon: 'la la-bell',
            title: '<strong>' + jsonData['message']['title'] + '</strong>: ',
            message: jsonData['message']['msg'],
            url: jsonData['message']['url'],
        }, {
            type: 'type' in jsonData['message'] ? jsonData['message']['type'] : 'info',
            placement: {
                from: 'bottom',
                align: 'right'
            }
        });
    };
});

