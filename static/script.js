document.addEventListener('DOMContentLoaded', () => {
  // === Category Dropdown Handling ===
  const selectWrapper = document.querySelector('.categorywrapper');
  const selectHeader = document.querySelector('.select-header');
  const categoryLabels = document.querySelectorAll('.category-label');
  const categoryInput = document.getElementById('categoryInput'); // hidden input in form

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
          categoryInput.value = option.dataset.value; // Update hidden input for Flask
          selectWrapper.classList.remove('open');
      });
  });

  // === Report Box Character Count ===
  const reportBox = document.getElementById('report');
  const charCount = document.getElementById('charcount');
  const errorMsg = document.getElementById('error');

  reportBox.addEventListener('input', function () {
      const len = reportBox.value.length;
      charCount.textContent = `*${len} / 1000`;

      if (len >= 20) {
          errorMsg.style.display = 'none';
      }
  });

  // === File Preview Handling ===
  const fileInput = document.getElementById("fileinput");
  const container = document.getElementById("container");

  function loadFile() {
      container.innerHTML += `<img src="${this.result}" />`;
  }

  function addMultipleFiles() {
      container.innerHTML = "";
      for (const file of this.files) {
          let reader = new FileReader();
          reader.addEventListener("load", loadFile);
          reader.readAsDataURL(file);
      }
  }

  fileInput.addEventListener("change", addMultipleFiles);

  // === About Section Toggle ===
  const aboutLink = document.getElementById("about");
  const aboutSection = document.getElementById("about-section");

  aboutLink.addEventListener("click", () => {
      if (aboutSection.style.display === "none" || aboutSection.style.display === "") {
          aboutSection.style.display = "block";
          aboutLink.textContent = "Now Scroll then Close Section With This Button";
      } else {
          aboutSection.style.display = "none";
          aboutLink.textContent = "About Page(learn more about the page)";
      }
  });
  // === Form Submission Validation ===
document.getElementById("reportForm").addEventListener("submit", async function(e) {
    e.preventDefault();
    console.log("FORM SUBMIT HANDLER FIRED");

    const categoryGroup = document.getElementById("category-group").value;
    const categoryItem = document.getElementById("options-group").value;
    const details = document.getElementById("report").value;
    const evidenceInput = document.getElementById("evidence");
    const reporterEmail = document.getElementById("reporter_email").value.trim();
    const fileInput = document.getElementById("fileinput");

    // Basic validation
    if (!categoryGroup || !categoryItem) {
        alert("Please select a category.");
        return;
    }
    if (details.length < 20) {
        alert("Enter at least 20 characters.");
        return;
    }
    if (evidenceInput && evidenceInput.value.trim()) {
        const urlPattern = /^(https?:\/\/)[\w.-]+\.[a-z]{2,}(\/.*)?$/i;
        if (!urlPattern.test(evidenceInput.value.trim())) {
            alert("Evidence must be a valid URL (starting with http:// or https://).");
            return;
        }
    }

    let evidenceUrls = [];

    // Add manual evidence URL if provided
    if (evidenceInput && evidenceInput.value.trim()) {
        evidenceUrls.push(evidenceInput.value.trim());
    }

    // If there are files selected, open Cloudinary widget
    if (fileInput.files && fileInput.files.length > 0) {
        await handleCloudinaryUpload(evidenceUrls, fileInput.files.length);
    }

    // If no files or after uploads complete, submit to backend
    await submitReport(evidenceUrls);
});

async function handleCloudinaryUpload(evidenceUrls, expectedFileCount) {
    return new Promise((resolve, reject) => {
        // Load Cloudinary script if not already loaded
        if (!window.cloudinary) {
            const script = document.createElement("script");
            script.src = "https://widget.cloudinary.com/v2.0/global/all.js";
            script.async = true;
            script.onload = openWidget;
            script.onerror = () => reject(new Error("Failed to load Cloudinary widget"));
            document.head.appendChild(script);
        } else {
          openWidget();
        }

        function openWidget() {
            let uploadedCount = 0;

            const widget = window.cloudinary.createUploadWidget(
                {
                    cloudName: "dowpqktts",              // ← REPLACE
                    uploadPreset: "evidence_uploads",      // ← REPLACE
                    sources: ["local", "url", "camera", "dropbox", "google_drive"],
                    multiple: true,
                    maxFiles: expectedFileCount,            // Optional: limit to selected files
                    cropping: false
                },
                (error, result) => {
                    if (error) {
                        console.error("Upload error:", error);
                        alert("Upload failed. Please try again.");
                        reject(error);
                        return;
                    }

                    if (result.event === "success") {
                        evidenceUrls.push(result.info.secure_url);
                        uploadedCount++;
                        console.log("Uploaded:", result.info.secure_url);
                    }

                    if (result.event === "close") {
                        if (uploadedCount === 0) {
                            // User closed without uploading anything
                            if (confirm("You closed the upload window without uploading any files. Continue without images?")) {
                                resolve();
                            } else {
                                reject(new Error("Upload cancelled"));
                            }
                        } else {
                            resolve(); // Proceed with whatever was uploaded
                        }
                    }
                }
            );
            widget.open();
    });
    
async function submitReport(evidenceUrls) {
    const formData = new FormData();
    formData.append("category_group", document.getElementById("category-group").value);
    formData.append("options_group", document.getElementById("options-group").value);
    formData.append("details", document.getElementById("report").value);
    formData.append("uploaded_urls", JSON.stringify(evidenceUrls));

    if (document.getElementById("reporter_email").value.trim()) {
        formData.append("reporter_email", document.getElementById("reporter_email").value.trim());
    }

    console.log("Sending to backend:", evidenceUrls);

    try {
        const res = await fetch("/", {  // Change "/" to your actual backend endpoint if different
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            const text = await res.text();
            throw new Error(`Server error ${res.status}: ${text}`);
        }

        alert("Report submitted successfully!");
        window.location.reload();
    } catch (err) {
        console.error("Submission failed:", err);
        alert("Failed to submit report. Please try again.");
    }
});

const fingerprintInput = document.getElementById('fingerprint');
if (fingerprintInput) {
      const cookieName = "anon_id";
      let anonId = getCookie(cookieName);
      if (!anonId) {
          anonId = "anon_" + crypto.randomUUID();
          setCookie(cookieName, anonId, 90); // 90 days
      }
      fingerprintInput.value = anonId;
  }

  // Helper functions for cookies
function setCookie(name, value, days) {
      const d = new Date();
      d.setTime(d.getTime() + (days*24*60*60*1000));
      const expires = "expires=" + d.toUTCString();
      document.cookie = name + "=" + value + ";" + expires + ";path=/";
  }

function getCookie(name) {
      const cname = name + "=";
      const decodedCookie = decodeURIComponent(document.cookie);
      const ca = decodedCookie.split(';');
      for (let i = 0; i < ca.length; i++) {
          let c = ca[i];
          while (c.charAt(0) === ' ') c = c.substring(1);
          if (c.indexOf(cname) === 0) return c.substring(cname.length, c.length);
      }
      return "";
  }
});
document.querySelectorAll(".options-group li").forEach(option => {
    option.addEventListener("click", function () {
        let group = this.getAttribute("data-group");
        let value = this.getAttribute("data-value");

        // Set hidden inputs
        document.getElementById("category-group").value = group;
        document.getElementById("options-group").value = value;

        // Optional UI preview
        document.querySelector(".select-header").textContent = group + " → " + value;
    });
});

const erudaScript = document.createElement('script');
erudaScript.src = 'https://cdn.jsdelivr.net/npm/eruda';
erudaScript.onload = () => {
    if (/Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
        eruda.init();
        console.log("Eruda initialized");
    }
};
document.body.appendChild(erudaScript);
