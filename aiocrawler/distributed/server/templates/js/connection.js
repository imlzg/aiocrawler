let connectionTable = $('#connection-table');

function tableAction(params){
		let url = '';
		if (params['command'] === 'agree')
			url = '/api/server/connection/auth/' + params['id'];
		else if (params['command'] === 'ban')
			url = '/api/server/blacklist/put/' + params['remote'];
		else
			url = '/api/server/connection/remove/' + params['id'];

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
						connectionTable.bootstrapTable('remove', {field: 'id', values: [params['id']]});
						notify({msg: data['msg']});
					}else{
						notify({msg: data['msg']});
					}
				}
			}
		});
}

function createConnectionTable(){
	createTable({
		table: connectionTable,
		url: '/api/server/connection/list',
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
						}) + ")'><i class='fa fa-ban'></i> Ban</button>\t";

						data += "<button class='btn btn-danger' onclick='tableAction(" + JSON.stringify({
							command: 'remove',
							id: row.id
						}) + ")'><i class='fa fa-remove'></i> Remove</button>";
						return data;
					}
				}],
	});
}

$(document).ready(() => {
	createConnectionTable();
});