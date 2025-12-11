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
document.getElementById("submitbtn").addEventListener("click", function (e) {
    e.preventDefault();

    const categoryGroup = document.getElementById("category-group").value;
    const categoryItem = document.getElementById("options-group").value;
    const details = document.getElementById("report").value;
    const evidenceInput = document.getElementById("evidence"); // FIXED

    if (!categoryGroup || !categoryItem) {
        alert("Please select a category.");
        return;
    }

    if (details.length < 20) {
        alert("Enter at least 20 characters.");
        return;
    }

    // Validate evidence URL BEFORE submitting
    if (evidenceInput && evidenceInput.value.trim().length > 0) {
        const urlPattern = /^(https?:\/\/)[\w.-]+\.[a-z]{2,}(\/.*)?$/i;
        if (!urlPattern.test(evidenceInput.value.trim())) {
            alert("Evidence must be a valid URL (starting with http:// or https://).");
            return;
        }
    }

    const formData = new FormData();
    formData.append("category_group", categoryGroup);
    formData.append("options_group", categoryItem);
    formData.append("details", details);

    if (evidenceInput && evidenceInput.value.trim() !== "") {
        formData.append("evidence", evidenceInput.value.trim());
    }

    const files = document.getElementById("fileinput").files;
    for (let f of files) {
        formData.append("fileinput", f);
    }

    fetch("/", {
        method: "POST",
        body: formData
    })
    .then(async res => {
        if (!res.ok) {
            const text = await res.text();
            console.log("Server error:", text);  // DEBUG
            alert("Server error: " + res.status);
            return;
        }
        window.location.reload();
    })
    .catch(err => {
        alert("Error submitting report");
        console.error(err);
    });
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