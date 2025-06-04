// Dashboard specific JavaScript

function waterPlants() {
    alert('Watering plants activated!');
    // Add your plant watering logic here
}

function toggleVentilation() {
    const btn = event.target.closest('i');
    if (btn) {
        alert('Ventilation system toggled!');
        // Add your ventilation control logic here
    }
}

function toggleLight() {
    const btn = event.target.closest('i');
    if (btn) {
        alert('Light source toggled!');
        // Add your light control logic here
    }
}