/**
 * BUTTON CLICK HANDLERS
 *
 * Each button on the homepage has its own handler function below.
 * Replace the placeholder console.log with your own implementation.
 */

function onButton1Click() {
  window.location.href = "random_dog_api.html";
}

function onButton2Click() {
  window.location.href = "quotes.html";
}

function onButton3Click() {
  // Navigate to Cat Facts page
  // API: https://catfact.ninja/fact
  // Returns: { fact: "string", length: number }
  // Displays: Random educational facts about cats
  window.location.href = "catfact.html";
}

function onButton4Click() {
  console.log("Button 4 clicked -- implement me!");
}

function onButton5Click() {
  window.location.href = "api-furkan.html";
}

async function onButton6Click() {
  try {
    const response = await fetch('https://jsonplaceholder.typicode.com/users/1');
    const data = await response.json();

    const newWindow = window.open("", "_blank");
    newWindow.document.write(`
      <h3>API Response</h3>
      <p><b>Description:</b> This data is a sample user profile retrieved from the JSONPlaceholder APIs.</p>
      <pre>${JSON.stringify(data, null, 2)}</pre>
    `);
    } catch (error) {
      alert("Error!");
    }
}

