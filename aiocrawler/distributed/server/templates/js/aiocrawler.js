function getNav() {
    let nav = {};
    $.ajax({
        url: '/api/user/nav',
        method: 'get',
        dataType: 'jsonp',
        async: false,
        success: (data) => {
            nav = data;
        }
    });
    return nav;
}

