
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
		pageList: [10, 25, 50, 100],
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

function websocket(){
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
                      updateHeaderInfo();
                      notify(jsonData['message']);
                  }
                };
            }
        },
        error: () => {
            notify({msg: 'Failed to connect websocket', type: 'danger'});
        }
    });
}

$(document).ready(() => {
    getHeader();
    websocket();
});
