
function notify(message){
    $.notify({
        icon: 'fa fa-bell-o',
        title: '<strong> Aiocrawler Notify</strong>',
        message: message['msg'],
        url: 'url' in message ? message['url'] : '#'
    },{
        allow_dismiss: true,
        type: 'type' in message ? message['type'] : 'info',
        placement: {
                from: 'bottom',
                align: 'right'
            }
    });
}

$(document).ready(() => {
    $.ajax({
        url: '/common/header',
        method: 'GET',
        dataType: 'jsonp',
        success: (data) => {
            if (data['status'] === 0) {
                $('#header').html(data['header']);
                let pathname = window.location.pathname;
                if (pathname === '/index' || pathname === '/')
                    $('#dashboard-li').addClass('nav-item active');
                else if (pathname === '/connection')
                    $('#connection-li').addClass('nav-item active');
                else if (pathname === '/crawler')
                    $('#crawler-li').addClass('nav-item active');
            }
            else
                notify({msg: data['msg']});
        },
        error: () => {
            notify({msg: 'Failed to get header', type: 'danger'});
        }
    });

    $.ajax({
        url: '/api/user/nav',
        method: 'get',
        dataType: 'jsonp',
        success: (data) => {
            if (data['status'] === 0)
            {
                let nav = data['data'];
                let currentHostPort = window.location.hostname + ':' + window.location.port;
                let websocket = new WebSocket('ws://' + currentHostPort + nav['websocket_url']);
                websocket.onmessage = (data) => {
                  let jsonData = JSON.parse(data.data);
                  if ('message' in jsonData){
                      notify(jsonData['message']);
                  }
                };
            }
        },
        error: () => {
            notify({msg: 'Failed to connect websocket', type: 'danger'});
        }
    });
});

