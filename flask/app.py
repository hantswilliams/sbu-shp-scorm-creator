from flask import Flask, render_template, request, send_file, jsonify
import markdown
import os
import zipfile
from jinja2 import Template
import xml.etree.ElementTree as ET
import re
import io
import tempfile

app = Flask(__name__)

# Function to generate sidebar
def generate_sidebar(md_content):
    slides = md_content.split('\n---\n')
    sidebar_html = '<ul id="sidebar-list" class="space-y-2">'
    for index, slide in enumerate(slides):
        lines = slide.strip().splitlines()
        for line in lines:
            match = re.match(r'^(#{1,2})\s+(.*)', line)
            if match:
                level = len(match.group(1))
                title = match.group(2)
                indent = (level - 1) * 4
                # Add a span for progress indicator and data-index attribute
                sidebar_html += f'<li class="ml-{indent} flex items-center"><a href="#/{index}" class="text-blue-500 hover:underline flex-1" data-index="{index}">{title}</a><span id="progress-{index}" class="ml-2 text-gray-400">⏺️</span></li>'
                break  # Only take the first matching header per slide
    sidebar_html += '</ul>'
    return sidebar_html

# Updated HTML Template with SCORM JavaScript code
html_template = Template('''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Your Course Title</title>
    <!-- Reveal.js -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/theme/black.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.min.js"></script>
    <!-- Reveal.js Markdown Plugin -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/plugin/markdown/markdown.min.js"></script>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            display: flex;
            min-height: 100vh;
            margin: 0;
        }
        #sidebar {
            min-width: 200px;
            background-color: #f7fafc; /* Tailwind gray-100 */
            padding: 1rem;
            overflow-y: auto;
        }
        #content {
            flex-grow: 1;
            overflow: hidden;
        }
        .reveal {
            height: 100vh;
        }
        .pointer-events-none {
            pointer-events: none;
        }
    </style>
    <script type="text/javascript">
        // SCORM API Wrapper
        var scorm = {
            api: null,
            initialized: false,
            findAPI: function(win) {
                var attempts = 0;
                while ((win.API == null) && (win.parent != null) && (win.parent != win)) {
                    attempts++;
                    if (attempts > 7) return null; // Prevent infinite loop
                    win = win.parent;
                }
                return win.API;
            },
            init: function() {
                this.api = this.findAPI(window);
                if (this.api == null) {
                    console.log("SCORM API not found.");
                    return false;
                }
                var result = this.api.LMSInitialize("");
                if (result.toString() != "true") {
                    console.log("LMS Initialize failed.");
                    return false;
                }
                this.initialized = true;
                return true;
            },
            finish: function() {
                if (this.initialized) {
                    var result = this.api.LMSFinish("");
                    if (result.toString() != "true") {
                        console.log("LMS Finish failed.");
                        return false;
                    }
                }
                return true;
            },
            setValue: function(name, value) {
                if (this.initialized) {
                    var result = this.api.LMSSetValue(name, value);
                    if (result.toString() != "true") {
                        console.log("LMS SetValue failed: " + name + " = " + value);
                    }
                }
            },
            getValue: function(name) {
                if (this.initialized) {
                    return this.api.LMSGetValue(name);
                }
                return "";
            },
            commit: function() {
                if (this.initialized) {
                    var result = this.api.LMSCommit("");
                    if (result.toString() != "true") {
                        console.log("LMS Commit failed.");
                    }
                }
            }
        };

        var totalSlides;
        var visitedSlides = [];

        function updateProgress(event) {
            // Mark the previous slide as visited
            if (event && typeof event.previousIndexh !== 'undefined') {
                var prevSlideIndex = event.previousIndexh;
                if (!visitedSlides.includes(prevSlideIndex)) {
                    visitedSlides.push(prevSlideIndex);
                }
            }

            // Mark the current slide as visited
            var currentSlideIndex = event ? event.indexh : Reveal.getIndices().h;
            if (!visitedSlides.includes(currentSlideIndex)) {
                visitedSlides.push(currentSlideIndex);
            }

            updateSidebar();

            // Update progress
            var progress = ((visitedSlides.length) / totalSlides) * 100;

            if (scorm.initialized) {
                scorm.setValue("cmi.core.lesson_location", currentSlideIndex.toString());
                scorm.setValue("cmi.core.lesson_status", "incomplete");

                // Save visited slides to suspend_data
                scorm.setValue("cmi.suspend_data", JSON.stringify(visitedSlides));

                scorm.setValue("cmi.core.score.raw", progress.toFixed(2));
                scorm.commit();
            }
        }

        function updateSidebar() {
            visitedSlides.forEach(function(index) {
                var progressElement = document.getElementById('progress-' + index);
                if (progressElement) {
                    progressElement.textContent = '✔️';
                    progressElement.classList.remove('text-gray-400');
                    progressElement.classList.add('text-green-500');
                }
            });
            lockSections();
        }

        function lockSections() {
            var sidebarLinks = document.querySelectorAll('#sidebar-list a');
            sidebarLinks.forEach(function(link) {
                var index = parseInt(link.getAttribute('data-index'));
                if (isNaN(index)) return;

                if (visitedSlides.includes(index - 1) || index === 0) {
                    // Unlock the link
                    link.classList.remove('pointer-events-none', 'text-gray-400');
                    link.classList.add('text-blue-500', 'hover:underline');
                    link.onclick = function() { Reveal.slide(index); };
                    link.removeAttribute('aria-disabled');
                } else {
                    // Lock the link
                    link.classList.add('pointer-events-none', 'text-gray-400');
                    link.classList.remove('text-blue-500', 'hover:underline');
                    link.onclick = function(event) { event.preventDefault(); };
                    link.setAttribute('aria-disabled', 'true');
                }
            });
        }

        function completeCourse() {
            if (scorm.initialized) {
                scorm.setValue("cmi.core.lesson_status", "completed");
                scorm.commit();
                scorm.finish();
                alert("Course completed. You may now close this window.");
                // Optionally, close the window
                // window.close();
            } else {
                alert("SCORM is not initialized.");
            }
        }

        // Initialize SCORM and Reveal.js on page load
        window.onload = function() {
            if (scorm.init()) {
                // Retrieve visited slides from suspend_data
                var savedVisited = scorm.getValue("cmi.suspend_data");
                if (savedVisited) {
                    visitedSlides = JSON.parse(savedVisited);
                }

                var savedLocation = scorm.getValue("cmi.core.lesson_location");
                Reveal.initialize({
                    hash: true,
                    plugins: [ RevealMarkdown ],
                    markdown: {
                        html: true // Allow HTML in Markdown
                    }
                });
                totalSlides = Reveal.getTotalSlides();
                if (savedLocation) {
                    Reveal.slide(Number(savedLocation));
                }
                scorm.setValue("cmi.core.lesson_status", "incomplete");
                scorm.commit();
                updateSidebar();
                // Call updateProgress on 'ready' event
                Reveal.on('ready', function(event) {
                    updateProgress(event);
                });
            } else {
                // Initialize Reveal.js even if SCORM is not initialized
                Reveal.initialize({
                    hash: true,
                    plugins: [ RevealMarkdown ],
                    markdown: {
                        html: true
                    }
                });
                totalSlides = Reveal.getTotalSlides();
                updateSidebar();
                Reveal.on('ready', function(event) {
                    updateProgress(event);
                });
            }

            // Disable skipping slides
            document.addEventListener('keydown', function(event) {
                var indices = Reveal.getIndices();
                var nextIndex = indices.h + 1;

                if (event.key === 'ArrowRight' || event.key === 'PageDown') {
                    if (!visitedSlides.includes(nextIndex - 1) && nextIndex !== 0) {
                        event.preventDefault();
                    }
                }
            });
        };

        // Update progress on slide change
        Reveal.on('slidechanged', function(event) {
            updateProgress(event);
        });
    </script>
</head>
<body>
    <div id="sidebar">
        {{ sidebar }}
    </div>
    <div id="content">
        <div class="reveal">
            <div class="slides">
                <section data-markdown data-separator="^---$" data-separator-notes="^Note:">
                    <textarea data-template>
{{ md_content }}
                    </textarea>
                </section>
            </div>
        </div>
    </div>
</body>
</html>
''')

# Route to serve the main page
@app.route('/')
def index():
    return render_template('index.html')

# Route to generate the SCORM package
@app.route('/generate_scorm', methods=['POST'])
def generate_scorm():
    try:
        data = request.get_json()
        if not data or 'markdown' not in data:
            return jsonify({'error': 'No markdown content provided'}), 400

        md_content = data['markdown']

        # Generate the sidebar HTML
        sidebar_html = generate_sidebar(md_content)

        # Render the HTML content
        html_content = html_template.render(md_content=md_content, sidebar=sidebar_html)

        # Create a temporary directory to store SCORM files
        with tempfile.TemporaryDirectory() as temp_dir:
            content_dir = os.path.join(temp_dir, 'content')
            os.makedirs(content_dir, exist_ok=True)

            # Save the HTML file
            index_html_path = os.path.join(content_dir, 'index.html')
            with open(index_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Optionally, save the Markdown content to a file (if needed)
            # md_file_path = os.path.join(content_dir, 'lesson.md')
            # with open(md_file_path, 'w', encoding='utf-8') as f:
            #     f.write(md_content)

            # Generate imsmanifest.xml
            manifest = ET.Element('manifest', {
                'identifier': 'CourseID',
                'version': '1.0',
                'xmlns': 'http://www.imsproject.org/xsd/imscp_rootv1p1p2',
                'xmlns:adlcp': 'http://www.adlnet.org/xsd/adlcp_rootv1p2',
                'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xsi:schemaLocation': 'http://www.imsproject.org/xsd/imscp_rootv1p1p2 \
                ims_xml.xsd http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd'
            })

            # Metadata
            metadata = ET.SubElement(manifest, 'metadata')
            schemav = ET.SubElement(metadata, 'schema')
            schemav.text = 'ADL SCORM'
            schemavv = ET.SubElement(metadata, 'schemaversion')
            schemavv.text = '1.2'

            # Organizations
            organizations = ET.SubElement(manifest, 'organizations', {'default': 'ORG1'})
            organization = ET.SubElement(organizations, 'organization', {'identifier': 'ORG1'})
            title = ET.SubElement(organization, 'title')
            title.text = 'Your Course Title'

            item = ET.SubElement(organization, 'item', {'identifier': 'ITEM1', 'identifierref': 'RES1'})
            item_title = ET.SubElement(item, 'title')
            item_title.text = 'Lesson 1'

            # Resources
            resources = ET.SubElement(manifest, 'resources')
            resource = ET.SubElement(resources, 'resource', {
                'identifier': 'RES1',
                'type': 'webcontent',
                'adlcp:scormtype': 'sco',
                'href': 'index.html'
            })
            file_elem = ET.SubElement(resource, 'file', {'href': 'index.html'})

            # Save imsmanifest.xml
            manifest_path = os.path.join(content_dir, 'imsmanifest.xml')
            tree = ET.ElementTree(manifest)
            tree.write(manifest_path, encoding='utf-8', xml_declaration=True)

            # Package into ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(content_dir):
                    for file in files:
                        filepath = os.path.join(root, file)
                        arcname = os.path.relpath(filepath, content_dir)
                        zf.write(filepath, arcname)

            zip_buffer.seek(0)

            # Send the ZIP file as a response
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name='scorm_package.zip',
                mimetype='application/zip'
            )
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
