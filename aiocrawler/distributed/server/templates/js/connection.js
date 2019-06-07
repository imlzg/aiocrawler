let connection_table = $('#connection-table');

function tableAction(action, params){
    let url = '';
    if (action === 'agree')
        url = '/api/server/verify/' + params['uuid'];
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
            if (data['statues'] === 0)
            {
                notify({msg: data['msg']});
                connection_table.bootstrapTable('remove', {field: 'uuid', values: params['uuid']});
            }else{
                notify({msg: data['msg']});
            }
        }
    }
});
}

$(document).ready(() => {
    	connection_table.bootstrapTable({
			url: '/api/server/get_unverified',
			method: 'GET',
			dataType: 'jsonp',
			checkboxEnabled: true,
			striped: true,
			cache: false,
			pagination: true,
			sidePagination: 'server',
			pageNumber: 1,
			pageSize: 5,
			pageList: [10, 25, 50, 100],
			search: false,
			idField: 'uuid',
			showRefresh: true,
			showColumns: true,
			clickToSelect: true,
			uniqueId: 'uuid',
			singleSelect: true,
			queryParamsType: '',
			queryParams: (params) => {
				return {
					pageNumber: params.pageNumber,
					pageSize: params.pageSize
				};
			},
			columns: [
				{
					field: 'uuid',
					title: 'UUID',
					align: 'center',
					formatter: (value, row) => {
						return row.uuid;
					}
				},
				{
					field: 'remote',
					title: 'Remote IP',
					align: 'center',
					formatter: (value, row) => {
						return row.remote;
					}
				},
				{
					field: 'host',
					title: 'Host',
					align: 'center',
					formatter: (value, row) => {
						return row.host;
					}
				},
				{
					filed: 'hostname',
					title: 'Hostname',
					align: 'center',
					formatter: (value, row) => {
						return row.hostname;
					}
				},
				{
					filed: 'last',
					title: 'Last Request',
					align: 'center',
					formatter: (value, row) => {
						return new Date(parseInt(row.last) * 1000).toDateString();
					}
				},
				{
					field: 'action',
					title: 'Action',
					formatter: (value, row) => {
						let data = '';
						data += "<a href= '#' onclick='tableAction(\"agree\", " + JSON.stringify({uuid: row.uuid}) + ");'><i class='fa fa-check-circle-o'></i> Agree</a>\t";
						data += "<a href= '#' onclick='tableAction(\"ban\", " + JSON.stringify({uuid: row.uuid, remote: row.remote}) + ")'><i class='fa fa-ban'></i> Ban</a>\t";
						data += "<a href= '#' onclick='tableAction(\"remove\", " + JSON.stringify({uuid: row.uuid}) + ")'><i class='fa fa-remove'></i> Remove</a>";
						return data;
					}
				}
		],
		onLoadError: () => {
			notify({msg: 'Failed to load connection data', type: 'danger'});
		}
	});

});