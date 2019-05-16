function getNav() {
    let nav = {};
    $.ajax({
        url: '/api/user/nav',
        method: 'get',
        dataType: 'jsonp',
        async: false,
        success: (data) => {
            if ('data' in data)
                nav = data['data'];
        }
    });
    return nav;
}

function getPublicKey(){
    let publicKey = '';
    $.ajax({
        url: '/api/user/pub',
        method: 'get',
        async: false,
        dataType: 'jsonp',
        success: (data) => {
            if ('pub' in data)
                publicKey = data['pub'];
        }
    });
    return publicKey;
}

