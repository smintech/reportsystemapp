document.addEventListener('DOMContentLoaded', () => {
    // ==================== ELEMENTS ====================
    const selectWrapper     = document.querySelector('.categorywrapper');
    const selectHeader      = document.querySelector('.select-header');
    const categoryLabels    = document.querySelectorAll('.category-label');
    const reportBox         = document.getElementById('report');
    const charCount         = document.getElementById('charcount');
    const errorMsg          = document.getElementById('error');
    const fileInput         = document.getElementById('fileinput');
    const container         = document.getElementById('container');
    const aboutLink         = document.getElementById('about');
    const aboutSection      = document.getElementById('about-section');
    const evidenceInput     = document.getElementById('evidence');
    const reporterEmailInput= document.getElementById('reporter_email');
    const fingerprintInput  = document.getElementById('fingerprint');
    const reportForm        = document.getElementById('reportForm');

    // ==================== CATEGORY DROPDOWN (Your original) ====================
    if (selectHeader && selectWrapper) {
        selectHeader.addEventListener('click', () => {
            selectWrapper.classList.toggle('open');
        });

        document.addEventListener('click', (event) => {
            if (!selectWrapper.contains(event.target)) {
                selectWrapper.classList.remove('open');
            }
        });

        categoryLabels.forEach(label => {
            label.addEventListener('click', (event) => {
                event.stopPropagation();
                const parentGroup = label.closest('.category-group');
                parentGroup.classList.toggle('expanded');
            });
        });

        const options = document.querySelectorAll('.options-group li');
        options.forEach(option => {
            option.addEventListener('click', (event) => {
                event.stopPropagation();
                selectHeader.textContent = option.textContent;
                // Assuming your options have data-value or similar — adjust if needed
                // If you use data-group and data-value, add here
                const group = option.dataset.group || option.closest('.category-group')?.querySelector('.category-label')?.textContent.trim();
                const value = option.dataset.value;

                document.getElementById("category-group").value = group || "";
                document.getElementById("options-group").value = value || option.textContent;

                selectWrapper.classList.remove('open');
            });
        });
    }

    // ==================== CHARACTER COUNT (Your original) ====================
    if (reportBox && charCount) {
        reportBox.addEventListener('input', function () {
            const len = reportBox.value.length;
            charCount.textContent = `*${len} / 1000`;

            if (len >= 20 && errorMsg) {
                errorMsg.style.display = 'none';
            }
        });
    }

    // ==================== YOUR ORIGINAL FILE PREVIEW LOGIC ====================
    if (fileInput && container) {
        function loadFile() {
            container.innerHTML += `<img src="${this.result}" />`;
        }

        function addMultipleFiles() {
            container.innerHTML = "";  // Clear previous
            for (const file of this.files) {
                let reader = new FileReader();
                reader.addEventListener("load", loadFile);
                reader.readAsDataURL(file);
            }
        }

        fileInput.addEventListener("change", addMultipleFiles);
    }

    // ==================== ABOUT SECTION TOGGLE (Your original) ====================
    if (aboutLink && aboutSection) {
        aboutLink.addEventListener("click", () => {
            if (aboutSection.style.display === "none" || aboutSection.style.display === "") {
                aboutSection.style.display = "block";
                aboutLink.textContent = "Now Scroll then Close Section With This Button";
            } else {
                aboutSection.style.display = "none";
                aboutLink.textContent = "About Page(learn more about the page)";
            }
        });
    }

    // ==================== SAFE ANONYMOUS ID ====================
    if (fingerprintInput) {
        const cookieName = "anon_id";
        let anonId = getCookie(cookieName);
        if (!anonId) {
            anonId = "anon_" + Date.now().toString(36) + Math.random().toString(36).substr(2);
            setCookie(cookieName, anonId, 90);
        }
        fingerprintInput.value = anonId;
    }

    // ==================== FORM SUBMISSION WITH DIRECT UPLOAD ====================
    reportForm.addEventListener("submit", async function(e) {
        e.preventDefault();
        console.log("FORM SUBMIT HANDLER FIRED");

        const categoryGroup = document.getElementById("category-group").value.trim();
        const categoryItem  = document.getElementById("options-group").value.trim();
        const details       = reportBox.value.trim();
        const manualLink    = evidenceInput.value.trim();
        const reporterEmail = reporterEmailInput.value.trim();

        // Validation
        if (!categoryGroup || !categoryItem) {
            alert("Please select a category.");
            return;
        }
        if (details.length < 20) {
            alert("Enter at least 20 characters.");
            return;
        }
        if (manualLink && !/^(https?:\/\/)/i.test(manualLink)) {
            alert("Evidence must be a valid URL (starting with http:// or https://).");
            return;
        }

        let evidenceUrls = [];
        if (manualLink) {
            evidenceUrls.push(manualLink);
        }

        // Direct silent upload if files selected
        if (fileInput.files.length > 0) {
            console.log(`Uploading ${fileInput.files.length} files to Cloudinary...`);
            const uploadedUrls = await uploadFilesDirectly(fileInput.files);

            if (uploadedUrls.length === 0) {
                if (!confirm("All files failed to upload. Continue without images?")) {
                    return;
                }
            } else {
                evidenceUrls = evidenceUrls.concat(uploadedUrls);
                console.log("Uploaded:", uploadedUrls);
            }
        }

        // Submit to backend
        await submitReport({
            categoryGroup,
            categoryItem,
            details,
            evidenceUrls,
            reporterEmail: reporterEmail || null
        });
    });

    // ==================== DIRECT CLOUDINARY UPLOAD (NO WIDGET) ====================
    async function uploadFilesDirectly(files) {
        const uploadedUrls = [];

        for (const file of files) {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("upload_preset", "evidence_uploads");  // Must be UNSIGNED

            try {
                const response = await fetch("https://api.cloudinary.com/v1_1/dowpqktts/image/upload", {
                    method: "POST",
                    body: formData
                });

                if (!response.ok) {
                    const err = await response.json();
                    console.error(`Failed: ${file.name} -`, err.error?.message);
                    continue;
                }

                const data = await response.json();
                if (data.secure_url) {
                    uploadedUrls.push(data.secure_url);
                }
            } catch (err) {
                console.error(`Error uploading ${file.name}:`, err);
            }
        }

        return uploadedUrls;
    }

    // ==================== SUBMIT TO BACKEND ====================
    async function submitReport({ categoryGroup, categoryItem, details, evidenceUrls, reporterEmail }) {
        const formData = new FormData();
        formData.append("category_group", categoryGroup);
        formData.append("options_group", categoryItem);
        formData.append("details", details);
        formData.append("uploaded_urls", JSON.stringify(evidenceUrls));

        if (reporterEmail) {
            formData.append("reporter_email", reporterEmail);
        }

        try {
            const response = await fetch("/", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                throw new Error("Server error");
            }

            alert("Report submitted successfully!");
            location.reload();
        } catch (err) {
            console.error(err);
            alert("Failed to submit report. Try again.");
        }
    }

    // ==================== COOKIE HELPERS ====================
    function setCookie(name, value, days) {
        const d = new Date();
        d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/;SameSite=Lax`;
    }

    function getCookie(name) {
        const cname = name + "=";
        const cookies = document.cookie.split(';');
        for (let c of cookies) {
            c = c.trim();
            if (c.startsWith(cname)) return c.substring(cname.length);
        }
        return "";
    }

    // ==================== ERUDA (Optional mobile debug) ====================
    if (/Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
        const erudaScript = document.createElement('script');
        erudaScript.src = 'https://cdn.jsdelivr.net/npm/eruda@3.4.3';
        erudaScript.onload = () => eruda.init();
        document.body.appendChild(erudaScript);
    }
});