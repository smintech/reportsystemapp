document.addEventListener('DOMContentLoaded', () => {
    // === Category Dropdown Handling (Your original, working perfectly) ===
    const selectWrapper = document.querySelector('.categorywrapper');
    const selectHeader = document.querySelector('.select-header');
    const categoryLabels = document.querySelectorAll('.category-label');

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

    // This one sets the hidden inputs and updates display
    const options = document.querySelectorAll('.options-group li');
    options.forEach(option => {
        option.addEventListener('click', (event) => {
            event.stopPropagation();
            const group = option.dataset.group || option.closest('.category-group').querySelector('.category-label').textContent.trim();
            const value = option.dataset.value;

            document.getElementById("category-group").value = group;
            document.getElementById("options-group").value = value;

            selectHeader.textContent = option.textContent.trim();
            selectWrapper.classList.remove('open');
        });
    });

    // === Report Box Character Count ===
    const reportBox = document.getElementById('report');
    const charCount = document.getElementById('charcount');
    const errorMsg = document.getElementById('error');

    if (reportBox && charCount) {
        reportBox.addEventListener('input', function () {
            const len = reportBox.value.length;
            charCount.textContent = `*${len} / 1000`;
            if (len >= 20 && errorMsg) {
                errorMsg.style.display = 'none';
            }
        });
    }

    // === File Preview Handling (Your original preview) ===
    const fileInput = document.getElementById("fileinput");
    const container = document.getElementById("container");

    if (fileInput && container) {
        function addMultipleFiles() {
            container.innerHTML = "";
            for (const file of fileInput.files) {
                if (file.type.startsWith('image/')) {
                    let reader = new FileReader();
                    reader.onload = function(e) {
                        container.innerHTML += `<img src="${e.target.result}" style="max-width:200px; margin:5px; border-radius:8px;" />`;
                    };
                    reader.readAsDataURL(file);
                }
            }
        }
        fileInput.addEventListener("change", addMultipleFiles);
    }

    // === About Section Toggle ===
    const aboutLink = document.getElementById("about");
    const aboutSection = document.getElementById("about-section");

    if (aboutLink && aboutSection) {
        aboutLink.addEventListener("click", (e) => {
            e.preventDefault();
            if (aboutSection.style.display === "none" || aboutSection.style.display === "") {
                aboutSection.style.display = "block";
                aboutLink.textContent = "Now Scroll then Close Section With This Button";
            } else {
                aboutSection.style.display = "none";
                aboutLink.textContent = "About Page(learn more about the page)";
            }
        });
    }

    // === Safe Anonymous ID (No crypto.randomUUID crash) ===
    const fingerprintInput = document.getElementById('fingerprint');
    if (fingerprintInput) {
        const cookieName = "anon_id";
        let anonId = getCookie(cookieName);

        if (!anonId) {
            anonId = "anon_" + Date.now().toString(36) + Math.random().toString(36).substr(2);
            setCookie(cookieName, anonId, 90);
        }
        fingerprintInput.value = anonId;
    }

    // === Cloudinary Upload + Form Submit (The new powerful one) ===
document.getElementById("reportForm").addEventListener("submit", async function(e) {
        e.preventDefault();
        console.log("FORM SUBMIT HANDLER FIRED");

        // Get form values
        const categoryGroup = document.getElementById("category-group").value.trim();
        const categoryItem = document.getElementById("options-group").value.trim();
        const details = document.getElementById("report").value.trim();
        const manualLink = evidenceInput?.value.trim() || "";
        const reporterEmail = reporterEmailInput?.value.trim() || "";

        // ===================== VALIDATION =====================
        if (!categoryGroup || !categoryItem) {
            alert("Please select a category and sub-option.");
            return;
        }

        if (details.length < 20) {
            alert("Details must be at least 20 characters.");
            return;
        }

        if (manualLink) {
            const urlPattern = /^(https?:\/\/)[\w.-]+\.[a-z]{2,}(\/.*)?$/i;
            if (!urlPattern.test(manualLink)) {
                alert("Evidence link must be a valid URL starting with http:// or https://");
                return;
            }
        }

        // ===================== COLLECT EVIDENCE URLs =====================
        let evidenceUrls = [];

        // Add manual evidence link if provided
        if (manualLink) {
            evidenceUrls.push(manualLink);
        }

        // Upload selected files directly to Cloudinary (no popup!)
        if (fileInput.files.length > 0) {
            console.log(`Uploading ${fileInput.files.length} file(s) to Cloudinary...`);
            try {
                const uploadedUrls = await uploadFilesDirectly(fileInput.files);
                evidenceUrls = evidenceUrls.concat(uploadedUrls);
                console.log("Successfully uploaded:", uploadedUrls);
            } catch (err) {
                console.error("Upload failed:", err);
                alert("Some files failed to upload. Please try again.");
                return;
            }
        }

        // ===================== SUBMIT TO BACKEND =====================
        await submitReport({
            categoryGroup,
            categoryItem,
            details,
            evidenceUrls,
            reporterEmail
        });
    });

    // ===================== DIRECT UPLOAD TO CLOUDINARY =====================
    async function uploadFilesDirectly(files) {
        const uploadedUrls = [];
        const uploadPromises = [];

        for (const file of files) {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("upload_preset", "evidence_uploads");  // Must be UNSIGNED preset
            formData.append("cloud_name", "dowpqktts");

            const promise = fetch("https://api.cloudinary.com/v1_1/dowpqktts/image/upload", {
                method: "POST",
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.secure_url) {
                    uploadedUrls.push(data.secure_url);
                } else {
                    throw new Error(data.error?.message || "Upload failed");
                }
            })
            .catch(err => {
                console.error(`Failed to upload ${file.name}:`, err);
                // Don't throw — allow other files to upload
            });

            uploadPromises.push(promise);
        }

        await Promise.all(uploadPromises);
        return uploadedUrls.filter(url => url); // Remove failed ones
    }

    // ===================== SUBMIT REPORT TO FLASK BACKEND =====================
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
                const errorText = await response.text();
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }

            alert("Report submitted successfully!");
            location.reload();
        } catch (err) {
            console.error("Submission failed:", err);
            alert("Failed to submit report. Check your connection and try again.");
        }
    }
});
    // Cookie helpers
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

    // === Eruda for mobile debugging (safe) ===
    if (/Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
        const erudaScript = document.createElement('script');
        erudaScript.src = 'https://cdn.jsdelivr.net/npm/eruda@3.4.3';
        erudaScript.onload = () => eruda.init();
        document.body.appendChild(erudaScript);
    }
});