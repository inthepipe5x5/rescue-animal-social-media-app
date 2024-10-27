document.addEventListener('DOMContentLoaded', function() {
    const rangeInput = document.getElementById('distance_filter_preference-input');
    const rangeDisplay = document.querySelector('span#distance_filter_preference-input');
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    
    let baseValue = parseInt(rangeInput.value);

    const updateRangeValue = () => {
        let increment = 0;
        checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                switch(checkbox.id) {
                    case 'willing_to_fly_by_airplane':
                        increment += 200;
                        break;
                    case 'willing_to_drive':
                        increment += 100;
                        break;
                    case 'willing_to_carpool':
                        increment += 50;
                        break;
                    case 'willing_to_volunteer_transport':
                        increment += 25;
                        break;
                }
            }
        });
        
        let newValue = Math.min(baseValue + increment, 500);
        rangeInput.value = newValue;
        rangeDisplay.textContent = `${newValue} Miles`;
    }
    
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateRangeValue);
    });
    
    // Update display and baseValue when range input changes
    rangeInput.addEventListener('input', function() {
        baseValue = parseInt(this.value);
        updateRangeValue();
    });
    
    // Initial update
    updateRangeValue();
});