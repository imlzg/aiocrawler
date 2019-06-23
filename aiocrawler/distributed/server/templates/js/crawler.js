let crawlerTable = $('#crawler-table');

function remove(uuid){
    let url = '/api/server/connection/remove/' + uuid;
    $.ajax({
        url: url,
        dataType: 'jsonp',
        success: (data) => {
            if (data['status'] === 0) {
                updateHeaderInfo();
                notify({msg: data['msg'], type: 'success'});
            }
            else
                notify({msg: data['msg'], type: 'warning'});
            crawlerTable.bootstrapTable('refresh');
        }
    });
}

function setting(uuid){

}

function createCrawlerTable() {
    createTable({
        table: crawlerTable,
        url: '/api/server/crawler/verified_list',
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
                    return '<a class="' + buttonClass[row.status] + '"> ' + statusString[row.status] + '</a>';
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
                    data += "<a class='" + buttonClass[row.status] +"' onclick=''><i class='fa fa-bug'></i> Projects</a>\t";
                    data += "<a class='" + buttonClass[row.status] + "' onclick='setting(" + row.uuid + ")'><i class='fa fa-cogs'></i> Setting</a>\t";
                    data += "<a class='btn btn-danger' onclick='remove(\"" + row.uuid + "\")'><i class='fa fa-remove'></i> Remove</a>";
                    return data;
                }
            }
        ]
    });
}

$(document).ready(() => {
    createCrawlerTable();
});