let crawlerTable = $('#crawler-table');

function remove(params){
    $.ajax({
        url: '/api/server/remove_client/' + params['uuid'],
        method: 'GET',
        dataType: 'jsonp',
        success: (data) => {
            if (data['status'] === 0)
            {
                updateHeaderInfo();
                notify({msg: data['msg'], type: 'success'});
                crawlerTable.bootstrapTable('remove', {field: 'id', values: params['id']});
            }
            else
                notify({msg: data['msg'], type: 'danger'});
        }
    });
}

function createCrawlerTable(){
    let statusString = ['disconnect', 'connected', 'error'];
    let buttonClass = ['btn btn-secondary', 'btn btn-success', 'btn btn-danger'];

    crawlerTable.bootstrapTable({
        url: '/api/server/get_verified',
        method: 'GET',
        dataType: 'jsonp',
        classes: 'table-borderless',
        clickToSelect: true,
        stripped: true,
        cache: false,
        pagination: true,
        sidePagination: 'server',
        queryParamsType: '',
        pageNumber: 1,
        pageSize: 5,
        pageList: [10, 25, 50, 100],
        search: false,
        showRefresh: true,
        showColumns: true,
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
                    return row.authorized_at;
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