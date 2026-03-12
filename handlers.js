/**
 * BUTTON CLICK HANDLERS
 *
 * Each button on the homepage has its own handler function below.
 * Replace the placeholder console.log with your own implementation.
 */

function onButton1Click() {
  console.log("Button 1 clicked -- implement me!");
}

function onButton2Click() {
  console.log("Button 2 clicked -- implement me!");
}

function onButton3Click() {
  console.log("Button 3 clicked -- implement me!");
}

function onButton4Click() {
  console.log("Button 4 clicked -- implement me!");
}

function onButton5Click() {
  console.log("Button 5 clicked -- implement me!");
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

