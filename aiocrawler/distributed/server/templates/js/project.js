let projectTable = $('#project-table');

function remove(id) {

}

function createProjectTable(){
    createTable({
        table: projectTable,
        url: '/api/server/project/list',
        sidePagination: 'client',
        search: true,
        columns: [
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
                title: 'Created At',
                align: 'center',
                formatter: (value, row) => {
                    return row['created_at'];
                }
            },
            {
                field: 'updated_at',
                title: 'Updated At',
                align: 'center',
                formatter: (value, row) => {
                    return row['updated_at'];
                }
            },
            {
                field: 'action',
                title: 'Action',
                align: 'center',
                formatter: (value, row) => {
                    let data = "<a class='btn btn-primary' onclick='edit(" + JSON.stringify({
                        projectName: row.name
                        }) + ")'><i class='fa fa-edit'></i> Edit</a>\t";
                    data += "<a class='btn btn-warning' onclick='createDeployTable(\"" + row.name + "\")'><i class='fa fa-cogs'></i> Deploy</a>\t";
                    data += "<a class='btn btn-danger' onclick='remove()'><i class='fa fa-remove'></i> Remove</a>";
                    return data;
                }
            }
        ]
    });
}

function UIMultiAddFile(id, file)
{
  let template = $('#files-template').text();
  template = template.replace('%%filename%%', file.name);

  template = $(template);
  template.prop('id', 'uploaderFile' + id);
  template.data('file-id', id);

  let files = $('#files');
  files.find('li.empty').fadeOut(); // remove the 'no files yet'
  files.prepend(template);
}

function UIMultiUpdateFileStatus(id, status, message)
{
  $('#uploaderFile' + id).find('span').html(message).prop('class', 'status text-' + status);
}

function UIMultiUpdateFileProgress(id, percent, color, active)
{
  color = (typeof color === 'undefined' ? false : color);
  active = (typeof active === 'undefined' ? true : active);

  let bar = $('#uploaderFile' + id).find('div.progress-bar');

  bar.width(percent + '%').attr('aria-valuenow', percent);
  bar.toggleClass('progress-bar-striped progress-bar-animated', active);

  if (percent === 0){
    bar.html('');
  } else {
    bar.html(percent + '%');
  }

  if (color !== false){
    bar.removeClass('bg-success bg-info bg-warning bg-danger');
    bar.addClass('bg-' + color);
  }
}

function createProjectUpload(){
    $('#drag-and-drop-zone').dmUploader({
        url: '/api/server/project/upload',
        allowedTypes: "tar|zip|tar.gz|tar.bz|tar.xz",
        onComplete: () => {
          projectTable.bootstrapTable('refresh');
          updateHeaderInfo();
        },
        onUploadSuccess: (id) => {
            UIMultiUpdateFileStatus(id, 'success', 'Upload complete');
            UIMultiUpdateFileProgress(id, 100, 'success', false);
        },
        onDragEnter: () => {
            this.addClass('active');
        },
        onDragLeave: () => {
            this.removeClass('active');
        },
        onNewFile: (id, file) => {
            UIMultiAddFile(id, file);
        },
        onBeforeUpload: (id) => {
            UIMultiUpdateFileStatus(id, 'uploading', 'Uploading...');
            UIMultiUpdateFileProgress(id, 0, '', true);
        },
        onUploadCanceled: (id) => {
            UIMultiUpdateFileStatus(id, 'warning', 'Cancel by user');
            UIMultiUpdateFileProgress(id, 0, 'warning', false);
        },
        onUploadProgress: (id, percent) => {
            UIMultiUpdateFileProgress(id, percent);
        },
        onUploadError: (id, xhr, status, message) => {
            UIMultiUpdateFileStatus(id, 'danger', JSON.parse(xhr.responseText).message);
            UIMultiUpdateFileProgress(id, 0, 'danger', false);
        },
        onFileTypeError: () => {
            notify({msg: 'Invalid file type', type: 'danger'});
        },
    });
}

function edit(params){
    let editor = CodeMirror.fromTextArea(document.getElementById('code'), {
        content: "Project Code",
        mode: "python",
        lineNumbers: true,
        lint: true,
        keyMap: "sublime",
        theme: "darcula",
        autofocus: true,
        lineWrapping: true,
        foldGutter: true,
        gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter", "CodeMirror-lint-markers"],
        matchBrackets: true,
        indentUnit: 4,
        autoCloseBrackets: true,
        styleActiveLine: true,
    });
    editor.on('keypress', () => {
        editor.showHint({completeSingle: false});
    });
    $('#edit-modal-title').text(params['projectName']);
    $('#edit-modal').modal('show');
}

function deploy(params){
    let deployButton = $('#deploy-' + params['uuid']);
    deployButton.text('Deploying');
    deployButton.addClass('fa fa-upload disabled');
    let url = '/api/server/project/deploy/name/' + params['projectName'] + '/uuid/' + params['uuid'];
    $.ajax({
        url: url,
        dataType: 'jsonp',
        success: (data) => {
            if (data['status'] !== 0)
            {
                $('#modal-text').text(data['msg']);
                deployButton.text('Error');
            }
            else
                deployButton.text('Deployed');
        }
    });
}

function createDeployTable(projectName){
    createTable({
        table: $('#deploy-table'),
        url: '/api/server/crawler/active_list',
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
                return '<a class="' + buttonClass[row.status] + ' disabled"> ' + statusString[row.status] + '</a>';
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
                let data = "";
                data += "<a class='btn btn-primary' onclick='deploy(" + JSON.stringify({
                    projectName: projectName,
                    uuid: row['uuid']
                }) + ")' id='deploy-" + row.uuid + "'><i class='fa fa-upload'></i> Deploy</a>";
                return data;
            }
        }]
    });
    $('#deploy-modal-title').text(projectName);
    $('#deploy-modal').modal('show');
}

$(document).ready(() => {
    createProjectTable();
    $('#upload-modal').on('show.bs.modal', () => {
        createProjectUpload();
    });
});