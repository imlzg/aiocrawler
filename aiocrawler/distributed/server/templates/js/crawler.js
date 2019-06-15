let crawlerTable = $('#crawler-table');

function createCrawlerTable() {
    let statusString = ['disconnect', 'connected', 'error'];
    let buttonClass = ['btn btn-secondary', 'btn btn-success', 'btn btn-danger'];
    createTable({
        table: crawlerTable,
        url: '/api/server/crawler/list',
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
                field: 'status',
                title: 'Status',
                align: 'center',
                formatter: (value, row) => {
                    return '<span class="' + buttonClass[row.status] + '"> ' + statusString[row.status] + '</span>';
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
                field: 'authorized_at',
                title: 'Authorized at',
                align: 'center',
                formatter: (value, row) => {
                    return row['authorized_at'];
                }
            },
            {
                field: 'action',
                title: 'Action',
                align: 'center',
                formatter: (value, row) => {
                    let data = '';
                    data += '<button class="btn btn-primary" id="edit-' + row.id + '"><i class="fa fa-edit"></i> Edit</button>\t';
                    data += '<button class="btn btn-warning" id="schedule-' + row.id + '"><i class="fa fa-cogs"></i> Schedule</button>\t';
                    data += '<button class="btn btn-danger" id="remove-' + row.id + '"><i class="fa fa-remove"></i> Remove</button>';
                    return data;
                }
            }
        ]
    });
}

$(document).ready(() => {
    createCrawlerTable();
});