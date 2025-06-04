// Plant control page specific JavaScript

function waterPlants() {
    alert('Watering plants activated!');
    document.getElementById('water-status').textContent = 'Watering...';
    document.querySelector('.status-item i.bx-water').className = 'bx bx-water status-active';

    // Simulate watering duration
    setTimeout(() => {
        document.getElementById('water-status').textContent = 'Standby';
        document.querySelector('.status-item i.bx-water').className = 'bx bx-water status-inactive';
    }, 3000);
}

function toggleVentilation() {
    const btn = event.target.closest('button');
    const statusText = document.getElementById('vent-status');
    const statusIcon = document.querySelector('.status-item i.bx-wind');

    if (btn.textContent.includes('Turn on')) {
        btn.innerHTML = '<i class="bx bx-wind"></i><span>Turn off Ventilation</span>';
        statusText.textContent = 'Running';
        statusIcon.className = 'bx bx-wind status-active';
        alert('Ventilation system turned ON');
    } else {
        btn.innerHTML = '<i class="bx bx-wind"></i><span>Turn on Ventilation</span>';
        statusText.textContent = 'Off';
        statusIcon.className = 'bx bx-wind status-inactive';
        alert('Ventilation system turned OFF');
    }
}

function toggleLight() {
    const btn = event.target.closest('button');
    const statusText = document.getElementById('light-status');
    const statusIcon = document.querySelector('.status-item i.bx-bulb');

    if (btn.textContent.includes('Turn on')) {
        btn.innerHTML = '<i class="bx bx-bulb"></i><span>Turn off Light Source</span>';
        statusText.textContent = 'On';
        statusIcon.className = 'bx bx-bulb status-active';
        alert('Light source turned ON');
    } else {
        btn.innerHTML = '<i class="bx bx-bulb"></i><span>Turn on Light Source</span>';
        statusText.textContent = 'Off';
        statusIcon.className = 'bx bx-bulb status-inactive';
        alert('Light source turned OFF');
    }
}