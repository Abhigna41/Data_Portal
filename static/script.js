let itemsData = [];

// --- Fetch items ---
async function fetchItems() {
  const table = document.getElementById("tableSelect").value;
  const itemSelect = document.getElementById("item");
  itemSelect.innerHTML = "<option>Loading...</option>";

  try {
    const res = await fetch(`/get_items?table=${table}`);
    const data = await res.json();
    itemsData = data;

    itemSelect.innerHTML = "<option value=''>--Select--</option>";
    if (data.length === 0) {
      itemSelect.innerHTML = "<option>No items found</option>";
      return;
    }

    data.forEach(obj => {
      const option = document.createElement("option");
      option.value = obj.Item;
      option.textContent = obj.Item;
      itemSelect.appendChild(option);
    });

    updateFieldsForTable(table);
  } catch (err) {
    console.error(err);
    itemSelect.innerHTML = "<option>Error loading items</option>";
  }
}

// --- Update form fields dynamically ---
function updateFieldsForTable(table) {
  const rateDiv = document.getElementById("rateFields");
  const totalDiv = document.getElementById("totalFields");

  if (table.toLowerCase() === "wasem") {
    rateDiv.innerHTML = `
      <label>G Rate:</label><input type="text" id="g_rate" readonly>
      <label>H Rate:</label><input type="text" id="h_rate" readonly>
    `;
    totalDiv.innerHTML = `
      <label>G Total:</label><input type="text" id="g_total" readonly>
      <label>H Total:</label><input type="text" id="h_total" readonly>
    `;
  } else {
    rateDiv.innerHTML = `<label>Rate:</label><input type="text" id="rate" readonly>`;
    totalDiv.innerHTML = `<label>Total:</label><input type="text" id="total" readonly>`;
  }

  document.getElementById("quantity").value = "";
}

// --- Autofill item ---
function autofillItem() {
  const table = document.getElementById("tableSelect").value;
  const selected = document.getElementById("item").value;
  const found = itemsData.find(obj => obj.Item === selected);
  if (!found) return;

  document.getElementById("code").value = found.Code || "";

  if (table.toLowerCase() === "wasem") {
    document.getElementById("g_rate").value = found.G_Rate || 0;
    document.getElementById("h_rate").value = found.H_Rate || 0;
    calculateTotal();
  } else {
    document.getElementById("rate").value = found.Rate || 0;
    calculateTotal();
  }
}

// --- Calculate totals ---
function calculateTotal() {
  const table = document.getElementById("tableSelect").value;
  const qty = parseFloat(document.getElementById("quantity").value) || 0;

  if (table.toLowerCase() === "wasem") {
    const gRate = parseFloat(document.getElementById("g_rate").value) || 0;
    const hRate = parseFloat(document.getElementById("h_rate").value) || 0;
    document.getElementById("g_total").value = (gRate * qty).toFixed(2);
    document.getElementById("h_total").value = (hRate * qty).toFixed(2);
  } else {
    const rate = parseFloat(document.getElementById("rate").value) || 0;
    document.getElementById("total").value = (rate * qty).toFixed(2);
  }
}

// --- Submit data ---
async function submitData() {
  const table = document.getElementById("tableSelect").value;
  const date = document.getElementById("date").value;
  const item = document.getElementById("item").value;
  const code = document.getElementById("code").value;
  const quantity = document.getElementById("quantity").value;

  let rate, total;

  if (table.toLowerCase() === "wasem") {
    const g_rate = document.getElementById("g_rate").value;
    const h_rate = document.getElementById("h_rate").value;
    rate = `G:${g_rate}|H:${h_rate}`;
    const g_total = document.getElementById("g_total").value;
    const h_total = document.getElementById("h_total").value;
    total = `G Total:${g_total}|H Total:${h_total}`;
  } else {
    rate = document.getElementById("rate").value;
    total = document.getElementById("total").value;
  }

  const payload = { table, date, item, code, rate, quantity, total };

  try {
    const res = await fetch("/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const msg = await res.text();
    alert(msg);
  } catch (err) {
    console.error(err);
    alert("Submission failed!");
  }
}
