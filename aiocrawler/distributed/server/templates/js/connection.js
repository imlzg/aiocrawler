let connectionTable = $('#connection-table');

function tableAction(params){
		let url = '';
		if (params['command'] === 'agree')
			url = '/api/server/auth/' + params['id'];
		else if (params['command'] === 'ban')
			url = '/api/server/put_into_blacklist/' + params['remote'];
		else
			url = '/api/server/remove_client/' + params['id'];

		$.ajax({
			url: url,
			method: 'GET',
			dataType: 'jsonp',
			success: (data) => {
				if (data['status'] === 0)
				{
					if (data['status'] === 0)
					{
						updateHeaderInfo();
						connectionTable.bootstrapTable('remove', {field: 'id', values: params['id']});
						notify({msg: data['msg']});
					}else{
						notify({msg: data['msg']});
					}
				}
			}
		});
}

function createConnectionTable(){
	    	connectionTable.bootstrapTable({
				url: '/api/server/get_unverified',
				method: 'GET',
				dataType: 'jsonp',
				striped: true,
				classes: 'table-borderless',
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
								data += "<button class='btn btn-primary' onclick='tableAction(" + JSON.stringify({
									command: 'agree',
									id: row.id
								}) + ")'><i class='fa fa-check'></i> Agree</button>\t";

								data += "<button class='btn btn-warning' onclick='tableAction(" + JSON.stringify({
									command: 'ban',
									id: row.id,
									remote: row.remote
								}) + ")'><i class='fa fa-check'></i> Ban</button>\t";

								data += "<button class='btn btn-danger' onclick='tableAction(" + JSON.stringify({
									command: 'remove',
									id: row.id
								}) + ")'><i class='fa fa-check'></i> Remove</button>";
								return data;
							}
						}
				],
				onLoadError: () => {
					notify({msg: 'Failed to load connection data', type: 'danger'});
				}
	});
}

$(document).ready(() => {
	createConnectionTable();
});