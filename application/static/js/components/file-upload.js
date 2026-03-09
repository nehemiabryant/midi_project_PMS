document.addEventListener('DOMContentLoaded', () => {
  initFileUpload();
});

function initFileUpload() {
  document.querySelectorAll('.drop-zone').forEach((zone) => {
    const input = zone.querySelector('input[type="file"]');
    const filenameEl = zone.querySelector('.drop-zone-filename');

    if (!input) {
      return;
    }

    zone.addEventListener('click', () => {
      input.click();
    });

    input.addEventListener('click', (event) => {
      event.stopPropagation();
    });

    input.addEventListener('change', () => {
      updateDropZone(zone, input, filenameEl);
    });

    zone.addEventListener('dragover', (event) => {
      event.preventDefault();
      zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', (event) => {
      event.preventDefault();
      zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (event) => {
      event.preventDefault();
      zone.classList.remove('dragover');

      const files = event.dataTransfer.files;
      if (!files.length) {
        return;
      }

      const file = files[0];
      if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        alert('File harus berupa PDF');
        return;
      }

      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      input.files = dataTransfer.files;
      updateDropZone(zone, input, filenameEl);
    });
  });
}

function updateDropZone(zone, input, filenameEl) {
  if (input.files && input.files.length > 0) {
    zone.classList.add('has-file');
    if (filenameEl) {
      filenameEl.textContent = input.files[0].name;
    }
    return;
  }

  zone.classList.remove('has-file');
  if (filenameEl) {
    filenameEl.textContent = '';
  }
}
