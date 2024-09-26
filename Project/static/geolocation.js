const createFlashMessage = (message, success = false) => {
  const errorContainer = document.getElementById("flash_message_container");
  const messageDiv = document.createElement("div");

  messageDiv.textContent = message;
  messageDiv.style.position = "fixed";
  messageDiv.style.top = "20px";
  messageDiv.style.right = "20px";
  messageDiv.style.padding = "10px";
  messageDiv.style.backgroundColor = success ? "green" : "red";
  messageDiv.style.color = "white";
  messageDiv.style.borderRadius = "5px";
  messageDiv.style.zIndex = "1000";
  messageDiv.style.opacity = "0";
  messageDiv.style.transition = "opacity 0.5s";
  messageDiv.style.marginTop = "60px";

  errorContainer.appendChild(messageDiv);

  setTimeout(() => {
    messageDiv.style.opacity = "1";
  }, 100);

  setTimeout(() => {
    messageDiv.style.opacity = "0";
    setTimeout(() => messageDiv.remove(), 500);
  }, 5000);
};

const getUserLocation = () => {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(
        createFlashMessage(
          "Geolocation is not supported by this browser.",
          false
        )
      );
    }
    createFlashMessage("Locating...", true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        resolve(`${latitude},${longitude}`);
      },
      (error) => {
        reject(error);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  });
};

const setGeolocation = async () => {
  const geolocationInput = document.querySelector("input#geolocation");

  try {
    const location = await getUserLocation();
    geolocationInput.value = location;
    console.log(
      geolocationInput.value,
      `geolocationInput.value || location;`,
      location
    );

    createFlashMessage("Geolocation set successfully!", true);
  } catch (error) {
    console.error("Error getting geolocation:", error);
    createFlashMessage("Error retrieving location: " + error.message, false);
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const geolocationInput = document.getElementById("geolocation");

  if (geolocationInput) {
    //Set the geolocation on page load if hidden geolocation form
    setGeolocation();
  } else {
    console.error("Geolocation Input not found");
  }
});
