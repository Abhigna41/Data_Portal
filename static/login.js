async function login(event) {
    event.preventDefault();  #stops from reloading page automatically

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();
    const message = document.getElementById("message");

    const response = await fetch("/login", {                   
        method: "POST",
        headers: { "Content-Type": "application/json" },        
        body: JSON.stringify({ username, password })                   
    });

    const result = await response.json();

    if (result.success) {
        message.textContent = "✅ Login successful! Redirecting...";
        message.style.color = "green";
        setTimeout(() => window.location.href = "/portal", 1000);
    } else {
        message.textContent = "❌ Invalid username or password.";
        message.style.color = "red";
    }
}
