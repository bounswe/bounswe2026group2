document.addEventListener("DOMContentLoaded", function () {
  var image = document.getElementById("dog-image");
  var loading = document.getElementById("loading");
  var error = document.getElementById("error");
  var nextDogButton = document.getElementById("next-dog-button");

  function loadDogImage() {
    loading.textContent = "Loading dog image...";
    error.textContent = "";
    image.style.display = "none";

    fetch("https://dog.ceo/api/breeds/image/random")
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Failed to fetch dog image");
        }
        return response.json();
      })
      .then(function (data) {
        image.src = data.message;
        image.style.display = "block";
        loading.textContent = "";
      })
      .catch(function () {
        loading.textContent = "";
        error.textContent = "Could not load a dog image. Please try again.";
      });
  }

  nextDogButton.addEventListener("click", loadDogImage);

  loadDogImage();
});