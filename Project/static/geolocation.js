
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

    errorContainer.appendChild(messageDiv);

    // Show message
    setTimeout(() => {
      messageDiv.style.opacity = "1";
    }, 100);

    // Hide after 3 seconds
    setTimeout(() => {
      messageDiv.style.opacity = "0";
      setTimeout(() => messageDiv.remove(), 500);
    }, 5000);
  };

  const getUserLocation = async () => {
    if (!navigator.geolocation) {
      throw new Error("Geolocation not supported.");
    }

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        position => {
          const { latitude, longitude } = position.coords;
          resolve(`${latitude},${longitude}`);
        },
        error => {
          createFlashMessage("Error retrieving location: " + error.message, false);
          reject(error);
        },
        {
          enableHighAccuracy: true,
          timeout: 5000,
          maximumAge: 0,
        }
      );
    });
  };

  document.addEventListener("DOMContentLoaded", async () => {
    const geolocationInput = document.getElementById("geolocation-input");

    try {
      const location = await getUserLocation();
      if (location) {
        geolocationInput.value = location;
        createFlashMessage("Geolocation set successfully!", true);
      }
    } catch (error) {
      console.error(error);
    }
  });

