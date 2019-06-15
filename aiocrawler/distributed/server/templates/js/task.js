let taskTable = $('#task-table');

function createTaskTable() {
	createTable({
		table: taskTable,
		url: '/api/sever/task/list',
		columns: [
			{
				field: 'id',
				title: 'ID',
				align: 'center',
				formatter: (value, row) => {
					return row['id'];
				}
			},
			{
				field: 'project_name',
				title: 'Project Name',
				align: 'center',
				formatter: (value, row) => {
					return row['project_name'];
				}
			},
			{
				field: 'created_at',
				title: 'Created At',
				align: 'center',
				formatter: (value, row) => {
					return row['created_at'];
				}
			},
			{
				field: 'start_time',
				title: 'Start Time',
				align: 'center',
				formatter: (value, row) => {
					return row['start_time'];
				}
			},
			{
				field: 'finished_time',
				title: 'Finished Time',
				align: 'center',
				formatter: (value, row) => {
					return row['finished_time'];
				}
			},
			{
				field: 'target',
				title: 'Target',
				align: 'center',
				formatter: (value, row) => {
					return row['target'];
				}
			},
			{
				field: 'action',
				title: 'Action',
				align: 'center',
				formatter: (value, row) => {
					let data  = "<button class='btn btn-primary'><i class='fa fa-eye'></i> Detail</button>";
					data += "<button class='btn btn-warning'><i class='fa fa-stop'></i> Stop</button>";
					data += "<button class='btn btn-danger'><i class='fa fa-remove'></i> Remove</button>";
					return data;
				}
			},
		]
	});
}

$(document).ready(() => {
	createTaskTable();
});