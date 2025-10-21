// script.js - Your original JavaScript code
let itemsData = [];

async function fetchItems() {
    const table = document.getElementById("tableSelect").value;
    if (!table) return;
    
    const res = await fetch(`/get_items?table=${table}`);
    itemsData = await res.json();

    const select = document.getElementById("item");
    select.innerHTML = "";
    
    // Add default option
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "-- Select an Item --";
    select.appendChild(defaultOption);
    
    itemsData.forEach(i => {
        const opt = document.createElement("option");
        opt.value = i.Item;
        opt.textContent = i.Item;
        select.appendChild(opt);
    });
    autofillItem();
}

function autofillItem() {
    const name = document.getElementById("item").value;
    const item = itemsData.find(i => i.Item === name);
    if(!item) {
        document.getElementById("code").value = "";
        document.getElementById("rate").value = "";
        document.getElementById("total").value = "";
        return;
    }
    document.getElementById("code").value = item.Code;
    if(item.G_Rate !== undefined && item.H_Rate !== undefined){
        document.getElementById("rate").value = `G: ${item.G_Rate} | H: ${item.H_Rate}`;
    } else {
        document.getElementById("rate").value = item.Rate || "";
    }
    calculateTotal();
}

function calculateTotal(){
    const qty = parseFloat(document.getElementById("quantity").value) || 0;
    const rateVal = document.getElementById("rate").value;
    let total = 0;
    
    if(rateVal.includes("G:")){
        const [g,h] = rateVal.replace("G:","").replace("H:","").split("|").map(x => parseFloat(x.trim()));
        total = `G Total: ${(g*qty).toFixed(2)} | H Total: ${(h*qty).toFixed(2)}`;
    } else {
        total = ((parseFloat(rateVal) || 0) * qty).toFixed(2);
    }
    document.getElementById("total").value = total;
}

async function submitData(){
    const table = document.getElementById("tableSelect").value;
    const date = document.getElementById("date").value;
    const item = document.getElementById("item").value;
    const code = document.getElementById("code").value;
    const rate = document.getElementById("rate").value;
    const quantity = document.getElementById("quantity").value;
    const total = document.getElementById("total").value;

    if (!table || !date || !item || !quantity) {
        alert("Please fill all required fields");
        return;
    }

    const res = await fetch("/submit", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({table, date, item, code, rate, quantity, total})
    });
    
    const result = await res.text();
    alert(result);
}

async function getDownloadLink(table, month) {
    const response = await fetch(`/download?table=${table}&month=${month}`);
    const data = await response.json();
    if (data.success) {
        document.getElementById('download_link').innerHTML =
            `<a href="${data.url}" target="_blank">Download CSV</a>`;
    } else {
        alert(data.message);
    }
}


document.getElementById("downloadBtn").addEventListener("click", async function() {
    const table = tableSelect.value;
    const month = monthSelect.value;

    if(!table || !month){
        alert("Please select table and month!");
        return;
    }

    try {
        const response = await fetch(`/download?table=${table}&month=${month}`);
        const data = await response.json();

        const linkDiv = document.getElementById("download_link");

        if(data.success){
            linkDiv.innerHTML = `<a href="${data.url}" target="_blank" class="btn btn-accent btn-block">
                                    <i class="fas fa-file-csv"></i> Click here to download CSV
                                </a>`;
        } else {
            linkDiv.innerHTML = `<p style="color:red;">${data.message}</p>`;
        }

    } catch(err){
        console.error(err);
        alert("Error fetching download link!");
    }
});
