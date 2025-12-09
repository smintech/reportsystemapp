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
  const reportForm = document.getElementById('reportForm');
  const evidenceInput = document.getElementById('evidence'); // separate evidence input

  reportForm.addEventListener('submit', (e) => {
      let valid = true;

      // Minimum report length
      if (reportBox.value.length < 20) {
          errorMsg.style.display = 'block';
          alert("Enter at least 20 characters for the report.");
          valid = false;
      }

      // Category selected
      if (!categoryInput.value) {
          alert("Please select a category for your report.");
          valid = false;
      }

      // Evidence optional: you can add extra validation if needed
      // Example: URL format check
      if (evidenceInput && evidenceInput.value.length > 0) {
          const urlPattern = /^(https?:\/\/)?([\w-]+)+([\w./?%&=-]*)?$/;
          if (!urlPattern.test(evidenceInput.value)) {
              alert("Evidence must be a valid URL or leave blank.");
              valid = false;
          }
      }

      if (!valid) {
          e.preventDefault(); // stop submission if invalid
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