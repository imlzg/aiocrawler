
let statusString = ['disconnected', 'connected', 'error'];
let buttonClass = ['btn btn-secondary disabled', 'btn btn-success', 'btn btn-secondary disabled'];

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

function getHeader(){
        $.ajax({
        url: '/api/server/get_header',
        method: 'GET',
        dataType: 'jsonp',
        success: (data) => {
            if (data['status'] === 0) {
                $('#header').html(data['header']);
                let pathname = window.location.pathname.split('/')[1];
                $('#' + pathname + '-li').addClass('active');
            }
            else
                notify({msg: data['msg']});
        },
        error: () => {
            notify({msg: 'Failed to get header', type: 'danger'});
        }
    });
}

function updateHeaderInfo() {
    $.ajax({
        url: '/api/server/get_info',
        dataType: 'jsonp',
        method: 'GET',
        success: (data) => {
            if (data['status'] === 0){
                $('#connection_count').text(data['connection_count']);
                $('#crawler_count').text(data['crawler_count']);
                $('#project_count').text(data['project_count']);
                $('#task_count').text(data['task_count']);
            }
            else{
                notify({msg: data['msg']});
            }
        }
    });
}

function createTable(setting){
    let defaultSetting ={
        sidePagination: 'server',
        search: false
    };
    $.extend(defaultSetting, setting);

    defaultSetting.table.bootstrapTable({
		url: defaultSetting.url,
		dataType: 'jsonp',
		stripped: true,
		classes: 'table-borderless',
		cache: false,
		pagination: true,
		sidePagination: defaultSetting.sidePagination,
		pageNumber: 1,
		pageSize: 5,
		search: defaultSetting.search,
		clickToSelect: true,
		queryParamsType: '',
		queryParams: (params) => {
			return {
				pageNumber: params.pageNumber,
				pageSize: params.pageSize
			};
		},
		columns: defaultSetting.columns,
		onLoadError: () => {
			notify({msg: 'Cannot load data from remote', type: 'danger'});
		}
	});
}

function createWebsocket(){
    $.ajax({
        url: '/api/user/websocket_url',
        dataType: 'jsonp',
        success: (data) => {
            if (data['status'] === 0) {
                let currentHostPort = window.location.hostname + ':' + window.location.port;
                let websocket = new WebSocket('ws://' + currentHostPort + data['websocket_url']);
                websocket.onmessage = (received_data) => {
                    received_data = JSON.parse(received_data.data);
                    if ('message' in received_data)
                        notify(received_data['message']);
                };
                websocket.onclose = () => {
                  console.log('websocket is closed');
                };
                websocket.onopen = () => {
                  console.log('connected to the server');
                };
            }else
                notify({msg: data['msg'], type: 'warning'});
        }
    });
}

$(document).ready(() => {
    getHeader();
    createWebsocket();
});
