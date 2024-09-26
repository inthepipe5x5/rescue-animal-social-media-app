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
          data.results.forEach((subdivision) => {
            const option = new Option(subdivision.name, subdivision.code);
            stateSelect.add(option);
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
      let = defaultCanadianValue = countrySelect.value === "CA" ? "ON" : "";
      const defaultOption = new Option("Select a state", defaultCanadianValue);
      stateSelect.add(defaultOption);
    }

    // Initial update of state options
    updateStateOptions();
  }
});
