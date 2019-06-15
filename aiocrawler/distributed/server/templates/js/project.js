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
                    let data = "<button class='btn btn-primary'><i class='fa fa-edit'></i> Edit</button>\t";
                    data += "<button class='btn btn-warning'><i class='fa fa-cogs'></i> Schedule</button>";
                    data += "<button class='btn btn-danger' onclick='remove()'><i class='fa fa-remove'></i> Remove</button>";
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
        allowedTypes: "tar|zip",
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

$(document).ready(() => {
    createProjectTable();
    $('#upload-modal').on('show.bs.modal', () => {
        createProjectUpload();
    });
});