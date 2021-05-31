function create_table(tab, color1, crypto){
    var tabulate = function (data,columns,colors) {
    //var table = d3.select('body').append('table')
    var table = d3.select(tab)
        var thead = table.append('thead')
        var tbody = table.append('tbody')

        thead.append('tr')
        .selectAll('th')
            .data(columns)
            .enter()
        .append('th')
            .text(function (d) { return d })

        var rows = tbody.selectAll('tr')
            .data(data)
            .enter()
        .append('tr')


        var cells = rows.selectAll('td')
            .data(function(row) {
                return columns.map(function (column) {
                    return { column: column, value: row[column] }
            })
        })
        .enter()
        .append('td')
        .text(function (d) { return d.value})
        .style("color", function (d, i) { return colors[i]})
        
    return table;
    }

    //var path = '../static/crypto_data/data/' + crypto.trim() + '_data.csv';
    var path = '../static/crypto_data/transactions/' + crypto.trim() + '.csv'+ '?' + Math.floor(Math.random() * 1000);
    d3.csv(path, function (data) {
        var columns = ['PRICE','AMOUNT','COIN']
        var colors = [color1, "white", "white"]
    tabulate(data,columns, colors)
    })
}


function create_table_right(tab, color1, file, crypto){
    var tabulate2 = function (data,columns,colors, scelto) {
    //var table = d3.select('body').append('table')
    var table = d3.select(tab)
        var thead = table.append('thead')
        var tbody = table.append('tbody')

        thead.append('tr')
        .selectAll('th')
            .data(columns)
            .enter()
        .append('th')
            .text(function (d) { return d })

        var rows = tbody.selectAll('tr')
            .data(data)
            .enter()
        .append('tr')


        var cells = rows.selectAll('td')
            .data(function(row) {
                return columns.map(function (column) {
                    return { column: column, value: row[column] }
            })
        })
        .enter()
        .append('td')
        .text(function (d) { return d.value})
        .style("color", function (d, i) {
            if (scelto=="True")
                if(i==2 && d.value >= 0) return "rgb(0, 255, 179)";
                else if(i==2) return "#ff0055";
                else return colors[i];
            else return colors[i];
        });
        
    return table;
    }

    if(file == "market")
    {
        var path = '../static/crypto_data/data/' + crypto.trim() + '_data.csv'+ '?' + Math.floor(Math.random() * 1000);
        d3.csv(path,function (data) {
            var columns = ['Date','Open','High', 'Low', 'Close', 'Volume', 'MarketCap']
            var colors = [color1, "white", "white", "white", "white", "white", "white"]
        tabulate2(data,columns, colors, "False")
        })
    }

    else if(file == "wallet")
    {
        if(crypto == "me")
        {
            var path = '../static/me.csv'+ '?' + Math.floor(Math.random() * 1000);
            d3.csv(path,function (data) {
                var columns = ["PRODUCT","AMOUNT"]
                var colors = [color1, "white"]
            tabulate2(data,columns, colors, "False")
            })

        }
        else if(crypto == "transactions_me")
        {
            var path =  "../static/transactions_me.csv"+ '?' + Math.floor(Math.random() * 1000);
            d3.csv(path,function (data) {
                var columns = ['DATE','PRODUCT','PRICE']
                var colors = [color1, "white", "white"]
            tabulate2(data,columns, colors, "True")
            })
        }
        
    }  
}