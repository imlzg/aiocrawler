let publicKey = getPublicKey();



$('#submit').click(() => {
    let encrypt = new JSEncrypt();
    encrypt.setPublicKey(publicKey);
    let password = encrypt.encrypt($('#password').val());
    let data = {
        username: $('#username').val(),
        password: password
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
                alertLabel.show();
                alertLabel.attr('class', 'alert alert-danger alert-dismissible fade show');
				$('#label-text').text(data['msg']);
            }
        }
    });
    return false;
});