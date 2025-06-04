// Image page specific JavaScript

let currentImage = null;

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Please select a valid image file.');
        return;
    }

    // Create FileReader to read the image
    const reader = new FileReader();
    reader.onload = function (e) {
        currentImage = e.target.result;
        displayImage(e.target.result);
        updateImageInfo(file);
    };
    reader.readAsDataURL(file);
}

function displayImage(imageSrc) {
    const container = document.getElementById('imageContainer');
    container.innerHTML = `
        <img src="${imageSrc}" alt="Uploaded plant image" class="uploaded-image">
        <div class="button-group" style="position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);">
            <button class="upload-btn" onclick="document.getElementById('imageInput').click()">
                <i class='bx bx-upload'></i> Choose New Image
            </button>
            <button class="analysis-btn" onclick="analyzeImage()">
                <i class='bx bx-search-alt'></i> Analyze Leaves
            </button>
        </div>
    `;
}

function updateImageInfo(file) {
    // Create a temporary image to get dimensions
    const img = new Image();
    img.onload = function () {
        document.getElementById('imageSize').textContent = `${this.width} x ${this.height}`;
    };
    img.src = URL.createObjectURL(file);

    // Reset other fields
    document.getElementById('leafCount').textContent = '--';
    document.getElementById('accuracy').textContent = '--';
    document.getElementById('timestamp').textContent = '--';
}

function analyzeImage() {
    if (!currentImage) {
        alert('Please upload an image first.');
        return;
    }

    // Show analyzing state
    document.getElementById('leafCount').innerHTML = '<span class="analyzing">Analyzing...</span>';
    document.getElementById('accuracy').innerHTML = '<span class="analyzing">Processing...</span>';
    document.getElementById('timestamp').innerHTML = '<span class="analyzing">Computing...</span>';

    // Simulate image analysis (replace with actual ML model integration)
    setTimeout(() => {
        // Generate mock analysis results
        const leafCount = Math.floor(Math.random() * 50) + 10; // Random between 10-60
        const accuracy = (Math.random() * 15 + 85).toFixed(1); // Random between 85-100%
        const analysisTime = (Math.random() * 2 + 1).toFixed(2); // Random between 1-3 seconds
        const currentTime = new Date().toLocaleTimeString();

        // Update results
        document.getElementById('leafCount').textContent = leafCount;
        document.getElementById('accuracy').textContent = accuracy + '%';
        document.getElementById('timestamp').textContent = currentTime;

        // Show success message
        alert(`Analysis complete! Detected ${leafCount} leaves with ${accuracy}% accuracy.`);
    }, 2000); // 2 second delay to simulate processing
}

// Reset upload area when no image is selected
function resetUploadArea() {
    const container = document.getElementById('imageContainer');
    container.innerHTML = `
        <div class="upload-area" id="uploadArea">
            <i class='bx bx-image'></i>
            <p>Upload an image to analyze leaf count</p>
            <div class="button-group">
                <button class="upload-btn" onclick="document.getElementById('imageInput').click()">
                    <i class='bx bx-upload'></i> Choose Image
                </button>
            </div>
            <input type="file" id="imageInput" accept="image/*" onchange="handleImageUpload(event)">
        </div>
    `;

    // Reset info cards
    document.getElementById('leafCount').textContent = '--';
    document.getElementById('accuracy').textContent = '--';
    document.getElementById('timestamp').textContent = '--';
    document.getElementById('imageSize').textContent = '--';
    currentImage = null;
}