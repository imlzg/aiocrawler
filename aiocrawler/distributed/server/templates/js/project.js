let projectTable = $('#project-table');

function createProjectTable(){
    projectTable.bootstrapTable({
        url: '/api/server/get_project',
        dataType: 'jsonp',
        classes: 'table-borderless',
        clickToSelect: true,
        cache: false,
        pagination: true,
        sidePagination: 'client',
        queryParamsType: '',
        pageNumber: 1,
        pageSize: 5,
        pageList: [10, 25, 50, 100],
        search: true,
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
                field: 'name',
                title: 'Project Name',
                align: 'center',
                formatter: (value, row) => {
                    return row.name;
                }
            },
            {
                field: 'created_at',
                title: 'Create At',
                align: 'center',
                formatter: (value, row) => {
                    return row.created_at;
                }
            },
            {
                field: 'updated_at',
                title: 'Updated At',
                align: 'center',
                formatter: (value, row) => {
                    return row.updated_at;
                }
            },
            {
                field: 'action',
                title: 'Action',
                align: 'center',
            }
        ]
    });
}

$(document).ready(() => {
    createProjectTable();
});