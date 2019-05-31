<!-- Initialize data -->
let interval = 5000;
let ctx = document.getElementById("chart");
let option = {
    title: {
        text: 'Item count',
    },
    tooltip: {
        trigger: 'axis',
        axisPointer: {
            animation: false
        }
    },
    xAxis: {
        type: 'time',
        splitLine: {
            show: false
        },
        name: 'time'
    },
    yAxis: {
        type: 'value',
        boundaryGap: [0, '10%'],
        splitLine: {
            show: true
        },
        name: 'count'
    },
    // visualMap: {
    //     top: 10,
    //     right: 10,
    //     pieces: [{
    //         gt: 0,
    //         lte: 30,
    //         color: '#096'
    //     }, {
    //         gt: 30,
    //         lte: 50,
    //         color: '#ffde33'
    //     }, {
    //         gt: 50,
    //         lte: 150,
    //         color: '#ff9933'
    //     }, {
    //         gt: 150,
    //         lte: 200,
    //         color: '#cc0033'
    //     }, {
    //         gt: 200,
    //         lte: 300,
    //         color: '#660099'
    //     }, {
    //         gt: 300,
    //         color: '#7e0023'
    //     }],
    //     outOfRange: {
    //         color: '#999'
    //     }
    // },
    series: [{
        name: 'Item count',
        type: 'line',
        showSymbol: false,
        smooth: false,
        itemStyle: {
            normal: {
                color: "#FF9933"
            },
            lineStyle: "#909878"
        }
    }]
};

let chart = echarts.init(ctx);
chart.setOption(option, true);
chart.showLoading();

function changeChart(itemInfo){
    chart.setOption({
        series: [{
            data: itemInfo
        }]
    })
}
function update(data){
    let itemInfo = data["item_info"];
    let itemCount = itemInfo.length > 0 ? itemInfo[itemInfo.length-1]["value"][1] : 0;
    $("#aiocrawler-count").html(data["aiocrawler_count"]);
    $("#item-count").html(itemCount);
    $("#downloaded-count").html(data["download_count"]);
    $("#request-count").html(data["request_count"]);
    changeChart(itemInfo);
}

function updateInfo(){
    $.ajax({
        url: 'update',
        method: 'GET',
        async: true,
        dataType: 'jsonp',
        jsonpCallback: 'update'
    });
}

$(document).ready(() => {
    updateInfo();
    chart.hideLoading();

});
window.onresize = () =>{
    chart.resize();
};

