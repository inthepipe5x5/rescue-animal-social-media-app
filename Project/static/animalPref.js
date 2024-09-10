const flashMessage = (message, success = false) => {
  const errorContainer = document.getElementById(
    "flash_message_container" //"animal-results-error-container"
  );
  // Create a div element for the error message
  const errorDiv = document.createElement("div");
  errorDiv.textContent = message;
  errorDiv.style.position = "fixed";
  errorDiv.style.top = "20px";
  errorDiv.style.right = "20px";
  errorDiv.style.padding = "10px";
  errorDiv.style.backgroundColor = success ? "green" : "#red"; // Red background for error // Green for success
  errorDiv.style.color = "white";
  errorDiv.style.borderRadius = "5px";
  errorDiv.style.zIndex = "1000";
  errorDiv.style.opacity = "0";
  errorDiv.style.transition = "opacity 0.5s";

  // Append the error message to the body
  errorContainer.appendChild(errorDiv);

  // Show the error message
  setTimeout(() => {
    errorDiv.style.opacity = "1";
  }, 10000);

  // Hide the error message after 3 seconds
  setTimeout(() => {
    errorDiv.style.opacity = "0";
    // Remove the error message from the DOM after fading out
    setTimeout(() => {
      errorDiv.remove();
    }, 500);
  }, 5000);

  console.debug(`${success ? "Success" : "Error"} flash message => ${message}`);
};

document.addEventListener("DOMContentLoaded", () => {
  const animalType = window.location.pathname.split("/").pop(); // Get animal_type from URL
  const form = document.querySelector("form");
  const selectFields = document.querySelectorAll("select");
  const booleanFields = document.querySelectorAll('input[type="checkbox"]');

  // Disable form fields initially
  form.querySelectorAll("input, select").forEach((field) => {
    field.disabled = true;
  });

  fetch(`/data/prefs/${animalType}`)
    .then((response) => response.json())
    .then((data) => {
      let prefs = data["results"];
      // Check if prefs received
      console.log(data["message"], "=>", prefs);
      if (prefs && Object.keys(prefs).length > 0) {
        flashMessage(
          `Prefs retrieved: ${data["success_flag"]} ${data["message"]}`,
          true
        );
        populateForm(prefs);
      } else {
        throw new Error(
          `Prefs retrieved: ${data["success_flag"]} ${data["message"]}`
        );
      }
    })
    .catch((err) => {
      console.error("Error fetching user preferences:", err);
      flashMessage(
        "No user preferences fetched, defaulting form values instead.",
        false
      );
      populateDefaults();
    })
    .finally(() => {
      // Enable form fields after data is fetched
      form.querySelectorAll("input, select").forEach((field) => {
        field.disabled = false;
      });
    });

  // Function to populate form with fetched data
  const populateForm = (prefs) => {
    // Boolean fields
    booleanFields.forEach((field) => {
      field.checked = prefs[field.name] || false;
    });

    // Select fields
    selectFields.forEach((select) => {
      if (prefs[select.name] && prefs[select.name].length > 0) {
        for (const option of select.options) {
          option.selected = prefs[select.name].includes(option.value);
        }
      } else {
        select.querySelector(`option[value="any"]`).selected = true;
      }
    });
  };

  // Function to populate default values
  const populateDefaults = () => {
    booleanFields.forEach((field) => {
      field.checked = false;
    });

    selectFields.forEach((select) => {
      select.querySelector(`option[value="any"]`).selected = true;
    });
  };

  // Add event listener to handle "any" option selection
  selectFields.forEach((select) => {
    select.addEventListener("change", function () {
      if (this.value.toLowerCase() === "any") {
        // If "any" is selected, select all options
        for (const option of this.options) {
          option.selected = true;
        }
      }
    });
  });
});
