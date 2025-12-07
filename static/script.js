document.addEventListener('DOMContentLoaded', () => {
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
  const options = document.querySelectorAll('.options-group li');
  options.forEach(option => {
      option.addEventListener('click', (event) => {
          event.stopPropagation();
          selectHeader.textContent = option.textContent;

          selectWrapper.classList.remove('open');
      });
  });
});
const reportBox = document.getElementById('report');
const charCount = document.getElementById('charcount');
const errorMsg = document.getElementById('error');
const submitBtn = document.getElementById('submitbtn');
const file = document.getElementById('fileinput');

reportBox.addEventListener('input', function () {
  const len = reportBox.value.length;

  charCount.textContent = `*${len} / 1000`;

  if (len >= 20) {
      errorMsg.style.display = 'none';
  }
});

submitBtn.addEventListener('click', async function () {
  if (reportBox.value.length < 20) {
      errorMsg.style.display = 'none';
      alert("Enter At least 20 Characters");
      return;
  }
  
  const category = document.querySelector('.select-header').textContent;
  const content = reportBox.value;
  
  try {
      const response = await fetch('/submit_report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category, content })
      });
      const data = await response.json();
      if (data.success) {
          alert("Report Submitted Successfully!");
          reportBox.value = "";
          file.value = "";
          charCount.textContent = "*0 / 1000";
          document.getElementById('container').innerHTML = "";
      } else {
          alert(data.message || "Error submitting report");
      }
  } catch (error) {
      alert("Error submitting report");
  }
});
document.addEventListener("DOMContentLoaded", () => {
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
});
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