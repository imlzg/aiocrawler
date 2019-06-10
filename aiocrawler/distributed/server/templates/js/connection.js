let connectionTable = $('#connection-table');

function tableAction(action, params){
    let url = '';
    if (action === 'agree')
        url = '/api/server/auth/' + params['uuid'];
    else if (action === 'ban')
        url = '/api/server/put_into_blacklist/' + params['remote'];
    else
        url = '/api/server/remove_client/' + params['uuid'];
    $.ajax({
		url: url,
		method: 'GET',
		dataType: 'jsonp',
		success: (data) => {
			if (data['status'] === 0)
			{
				if (data['status'] === 0)
				{
					getHeader();
					connectionTable.bootstrapTable('remove', {field: 'uuid', values: params['uuid']});
					notify({msg: data['msg']});
				}else{
					notify({msg: data['msg']});
				}
			}
		}
	});
}

$(document).ready(() => {
    	connectionTable.bootstrapTable({
			url: '/api/server/get_unverified',
			method: 'GET',
			dataType: 'jsonp',
			striped: true,
			cache: false,
			pagination: true,
			sidePagination: 'server',
			pageNumber: 1,
			pageSize: 5,
			pageList: [10, 25, 50, 100],
			search: false,
			showRefresh: true,
			showColumns: true,
			clickToSelect: true,
			queryParamsType: '',
			queryParams: (params) => {
				return {
					pageNumber: params.pageNumber,
					pageSize: params.pageSize
				};
			},
			columns: [
				{
					field: 'id',
					title: 'ID',
					align: 'center',
					formatter: (value, row) => {
						return row.id;
					}
				},
				{
					field: 'remote',
					title: 'Remote Host',
					align: 'center',
					formatter: (value, row) => {
						return row.remote;
					}
				},
				{
					field: 'host',
					title: 'Host/Hostname',
					align: 'center',
					formatter: (value, row) => {
						return row.host + '/' + row.hostname;
					}
				},
				{
					filed: 'last',
					title: 'Last Request',
					align: 'center',
					formatter: (value, row) => {
						return row.last;
					}
				},
				{
					field: 'action',
					title: 'Action',
					align: 'center',
					formatter: (value, row) => {
						let data = '';
						data += "<button class='btn btn-primary' onclick='tableAction(\"agree\", " + JSON.stringify({id: row.id, uuid: row.uuid}) + ");'><i class='fa fa-check-circle-o'></i> Agree</button>\t";
						data += "<button  class='btn btn-warning' onclick='tableAction(\"ban\", " + JSON.stringify({id: row.id, remote: row.remote}) + ")'><i class='fa fa-ban'></i> Ban</button>\t";
						data += "<button  class='btn btn-danger' onclick='tableAction(\"remove\", " + JSON.stringify({id: row.id, uuid: row.uuid}) + ")'><i class='fa fa-remove'></i> Remove</button>";
						return data;
					}
				}
		],
		onLoadError: () => {
			notify({msg: 'Failed to load connection data', type: 'danger'});
		}
	});

});