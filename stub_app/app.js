document.addEventListener("DOMContentLoaded", function () {
  var grid = document.getElementById("button-grid");

  for (var i = 0; i < NUM_BUTTONS; i++) {
    var label = BUTTON_LABELS[i] || "Button " + (i + 1);
    var handlerName = "onButton" + (i + 1) + "Click";
    var handler =
      typeof window[handlerName] === "function"
        ? window[handlerName]
        : createFallbackHandler(i + 1);

    var btn = document.createElement("button");
    btn.textContent = label;
    btn.addEventListener("click", handler);

    if (i == 6) {
      btn.addEventListener("click", AnkaraWeatherApiFunc);
    }

    grid.appendChild(btn);
  }
});

function createFallbackHandler(n) {
  return function () {
    console.log("Button " + n + " clicked -- no handler found");
  };
}

async function AnkaraWeatherApiFunc() {
  const url = "https://api.open-meteo.com/v1/forecast?latitude=39.92&longitude=32.85&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m";
  const response = await fetch(url);
  const data = await response.json();

  console.log(JSON.stringify(data, null, 2));

  const newWindow = window.open("", "_blank");

  newWindow.document.write(`
    <html>
      <head>
        <title>Ankara Weather</title>
      </head>
      <body>
        <h1>Ankara Weather Data</h1>
        <pre>${JSON.stringify(data, null, 2)}</pre>
      </body>
    </html>
  `);
}