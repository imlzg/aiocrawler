
$('#login-form').submit(() => {
    let data = {
        username: $('#username').val(),
        password: hex_sha1($('#password').val())
    };
    $.ajax({
        type: 'POST',
        url: '/api/user/login',
        data: data,
        dataType: 'jsonp',
        success: (data) => {
            if (data['status'] === 0)
                window.location.href = data['url'];
            else{
                let alertLabel = $('#alert');
                alertLabel.show();
                alertLabel.attr('class', 'alert alert-danger alert-dismissible fade show');
				$('#label-text').text(data['msg']);
            }
        }
    });
    return false;
});