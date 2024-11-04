document.addEventListener("DOMContentLoaded", function () {
  const countrySelect = document.querySelector('select[name="country"]');
  const stateSelect = document.querySelector('select[name="state"]');

  // Grab initial values
  const initialStateValue = stateSelect.value || "";
  const initialCountryValue = countrySelect.value || "";

  if (countrySelect && stateSelect) {
    countrySelect.addEventListener("change", updateStateOptions);

    async function updateStateOptions() {
      const selectedCountry = countrySelect.value;
      if (!selectedCountry) {
        clearStateOptions();
        return;
      }

      try {
        const response = await fetch(`/data/${selectedCountry}/state`);
        const data = await response.json();

        clearStateOptions();

        // Handle successful API request
        if (data.results.length > 0) {
          // Sort the results alphabetically by name
          data.results.sort((a, b) => a.name.localeCompare(b.name));

          let initialStateFound = false;
          const shouldFindInitialState = initialStateValue !== "" && 
                                         selectedCountry.toLowerCase() === initialCountryValue.toLowerCase();

          data.results.forEach((subdivision, index) => {
            // Capitalize the name for the label
            const capitalizedName = subdivision.name
              .split(" ")
              .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
              .join(" ");

            // Create option with capitalized name as label and code as value
            const option = new Option(capitalizedName, subdivision.code);
            stateSelect.add(option);

            // Check if this is the initial state (if initial state should be handled)
            if (shouldFindInitialState && 
                subdivision.name.toLowerCase() === initialStateValue.toLowerCase()) {
              option.selected = true;
              initialStateFound = true;
            }
          });

          // If no initial state but select the first option as default
          if (!initialStateFound) {
            stateSelect.selectedIndex = 0;
          }

          stateSelect.disabled = false;
        } else {
          const option = new Option("No states available", "");
          stateSelect.add(option);
          stateSelect.disabled = true;
        }
      } catch (error) {
        console.error("Error fetching state data:", error);
        clearStateOptions();
        const option = new Option("Error loading states", "");
        stateSelect.add(option);
        stateSelect.disabled = true;
      }
    }

    function clearStateOptions() {
      stateSelect.innerHTML = "";
    }

    // Initial update of state options
    updateStateOptions();
  }
});