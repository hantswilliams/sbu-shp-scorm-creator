// Initialize CodeMirror editor
var editor = CodeMirror(document.getElementById('editor'), {
    mode: 'markdown',
    lineNumbers: true,
    lineWrapping: true,
    theme: 'monokai',
});

// Set initial content
var initialMarkdown = `# Welcome to Your Slide Editor

Type your **Markdown** content here.

---

## Slide 2

- Bullet point 1
- Bullet point 2

---

## Slide 3

Add more content here.

---

`;
editor.setValue(initialMarkdown);

// Function to update the preview
function updatePreview() {
    var markdownText = editor.getValue();
    var slidesElement = document.querySelector('.reveal .slides');

    // Split the Markdown content into slides
    var slides = markdownText.split(/^---$/gm);
    var slidesHTML = slides.map(function(slideContent) {
        // Trim leading/trailing whitespace
        slideContent = slideContent.trim();
        return `<section data-markdown><textarea data-template>${slideContent}</textarea></section>`;
    }).join('\n');

    slidesElement.innerHTML = slidesHTML;

    // Reinitialize Reveal.js
    Reveal.initialize({
        hash: true,
        plugins: [ RevealMarkdown ],
        slideNumber: true,
        controls: true,
        progress: true,
        center: true,
        transition: 'slide',
    });

    // Apply the selected background color
    var selectedColor = document.getElementById('bgColorPicker').value;
    document.querySelector('.reveal').style.backgroundColor = selectedColor;
}

// Update preview initially
updatePreview();

// Remove the automatic update on editor change
// editor.on('change', function() {
//     updatePreview();
// });

// Implement the 'Update Preview' button functionality
document.getElementById('updatePreviewBtn').addEventListener('click', function() {
    updatePreview();
});

// Implement the download functionality
document.getElementById('downloadBtn').addEventListener('click', function() {
    var markdownText = editor.getValue();
    var blob = new Blob([markdownText], { type: 'text/markdown;charset=utf-8' });
    var link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.download = 'lesson.md';
    link.click();
});

// Implement the upload functionality
document.getElementById('uploadBtn').addEventListener('click', function() {
    document.getElementById('fileInput').click();
});

document.getElementById('fileInput').addEventListener('change', function(event) {
    var file = event.target.files[0];
    if (file && file.name.endsWith('.md')) {
        var reader = new FileReader();
        reader.onload = function(e) {
            editor.setValue(e.target.result);
        };
        reader.readAsText(file);
    } else {
        alert('Please select a Markdown (.md) file.');
    }
});

// Implement the fullscreen preview functionality
document.getElementById('fullscreenBtn').addEventListener('click', function() {
    var previewElement = document.getElementById('preview');
    if (previewElement.requestFullscreen) {
        previewElement.requestFullscreen();
    } else if (previewElement.webkitRequestFullscreen) { /* Safari */
        previewElement.webkitRequestFullscreen();
    } else if (previewElement.msRequestFullscreen) { /* IE11 */
        previewElement.msRequestFullscreen();
    }
});

// Event listener for background color picker
document.getElementById('bgColorPicker').addEventListener('input', function() {
    var selectedColor = this.value;
    document.querySelector('.reveal').style.backgroundColor = selectedColor;
});

// set a default background color of black

document.querySelector('.reveal').style.backgroundColor = 'grey';

// Implement the 'Generate SCORM Package' button functionality
document.getElementById('generateScormBtn').addEventListener('click', function() {
    var markdownText = editor.getValue();

    // Send the request to the Flask backend
    fetch('/generate_scorm', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ markdown: markdownText })
    })
    .then(function(response) {
        if (response.ok) {
            return response.blob();
        } else {
            return response.json().then(function(data) {
                throw new Error(data.error || 'Error generating SCORM package.');
            });
        }
    })
    .then(function(blob) {
        // Create a link to download the ZIP file
        var link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = 'scorm_package.zip';
        link.click();
    })
    .catch(function(error) {
        console.error('Error:', error);
        alert('An error occurred while generating the SCORM package:\n' + error.message);
    });
});

