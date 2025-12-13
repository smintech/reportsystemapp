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

        const categoryGroup = document.getElementById("category-group").value;
        const categoryItem = document.getElementById("options-group").value;
        const details = document.getElementById("report").value.trim();
        const evidenceInput = document.getElementById("evidence");
        const reporterEmail = document.getElementById("reporter_email").value.trim();

        // Validation
        if (!categoryGroup || !categoryItem) {
            alert("Please select a category and option.");
            return;
        }
        if (details.length < 20) {
            alert("Details must be at least 20 characters.");
            return;
        }
        if (evidenceInput?.value.trim()) {
            const urlPattern = /^(https?:\/\/)[\w.-]+\.[a-z]{2,}(\/.*)?$/i;
            if (!urlPattern.test(evidenceInput.value.trim())) {
                alert("Evidence link must be a valid URL starting with http:// or https://");
                return;
            }
        }

        let evidenceUrls = [];
        if (evidenceInput?.value.trim()) {
            evidenceUrls.push(evidenceInput.value.trim());
        }

        // Cloudinary upload if files selected
        if (fileInput.files.length > 0) {
            try {
                await handleCloudinaryUpload(evidenceUrls);
            } catch (err) {
                console.log("Upload cancelled or failed:", err);
                return; // Don't submit if user cancelled
            }
        }

        // Final submit
        await submitReport(evidenceUrls);
    });

    async function handleCloudinaryUpload(evidenceUrls) {
        return new Promise((resolve, reject) => {
            if (!window.cloudinary) {
                const script = document.createElement("script");
                script.src = "https://widget.cloudinary.com/v2.0/global/all.js";
                script.async = true;
                script.onload = openWidget;
                script.onerror = () => reject("Failed to load Cloudinary");
                document.head.appendChild(script);
            } else {
                openWidget();
            }

            function openWidget() {
                let uploaded = 0;
                const widget = window.cloudinary.createUploadWidget({
                    cloudName: "dowpqktts",
                    uploadPreset: "evidence_uploads",
                    sources: ["local", "url", "camera"],
                    multiple: true,
                    cropping: false
                }, (error, result) => {
                    if (error) {
                        alert("Upload error. Try again.");
                        reject(error);
                        return;
                    }
                    if (result.event === "success") {
                        evidenceUrls.push(result.info.secure_url);
                        uploaded++;
                    }
                    if (result.event === "close") {
                        if (uploaded === 0) {
                            if (confirm("No files uploaded. Continue without images?")) {
                                resolve();
                            } else {
                                reject("cancelled");
                            }
                        } else {
                            resolve();
                        }
                    }
                });
                widget.open();
            }
        });
    }

    async function submitReport(evidenceUrls) {
        const formData = new FormData();
        formData.append("category_group", document.getElementById("category-group").value);
        formData.append("options_group", document.getElementById("options-group").value);
        formData.append("details", document.getElementById("report").value.trim());
        formData.append("uploaded_urls", JSON.stringify(evidenceUrls));
        if (reporterEmail) formData.append("reporter_email", reporterEmail);

        try {
            const res = await fetch("/", {
                method: "POST",
                body: formData
            });

            if (!res.ok) throw new Error("Server error");

            alert("Report submitted successfully!");
            location.reload();
        } catch (err) {
            alert("Submission failed. Check connection and try again.");
        }
    }

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