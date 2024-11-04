document.addEventListener("DOMContentLoaded", function () {
  const countrySelect = document.querySelector('select[name="country"]');
  const stateSelect = document.querySelector('select[name="state"]');

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

        if (data.results.length > 0) {
          // Sort the results alphabetically by name
          data.results.sort((a, b) => a.name.localeCompare(b.name));
          
          data.results.forEach((subdivision, index) => {
            const option = new Option(subdivision.name, subdivision.code);
            stateSelect.add(option);
            
            // Select the first option by default
            if (index === 0) {
              option.selected = true;
            }
          });
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
      // Remove the default option as we'll be selecting the first state automatically
    }

    // Initial update of state options
    updateStateOptions();
  }
});