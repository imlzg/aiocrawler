let publicKey = getPublicKey();

$('#register-form').submit(() => {
    let jsEncrypt = new JSEncrypt();
    jsEncrypt.setPublicKey('MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCwjDm1HXDw8QH5ZtGMQIl2h/I8E+chOQA8aQ8xCR/+aHnROaN/ZU5Vmd2Zz7g6cAacR9BSm60+iSCYtvEGJKl0WqvbPGJkc8tedjNF1QqgWqkkuE6Udgw2OkEKJCxDg6PrAniR7Cc0io9G8bW4P8JDJjSbbafvMPDDFbVVUWJxxwIDAQAB');
    let password = jsEncrypt.encrypt($('#password').val());
    let data = {
        username: $('#username').val(),
        password: password
    };

    $.ajax({
        type: 'POST',
        url: '/api/user/register',
        data: data,
        dataType: 'jsonp',
        success: (data) => {
			if (data['status'] === 0)
				window.location.href = data['url'];
			else
			{
			    let alertLabel = $('#alert');
				alertLabel.show();
				alertLabel.attr('class', 'alert alert-danger alert-dismissible fade show');
				$('#label-text').text(data['msg']);
			}
        }
    });
    return false;
});