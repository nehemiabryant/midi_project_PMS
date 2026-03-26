document.addEventListener('DOMContentLoaded', () => {
  initCKEditors();
  initCKEditorFormSync();
});

function initCKEditors() {
  const richtextFields = document.querySelectorAll('textarea.richtext');
  if (!richtextFields.length || typeof CKEDITOR === 'undefined') {
    return;
  }

  richtextFields.forEach((textarea) => {
    CKEDITOR.replace(textarea.id, {
      height: 80,
      versionCheck: false,
      removePlugins: 'elementspath',
      resize_enabled: false,
      toolbar: [
        { name: 'styles', items: ['Format', 'Font', 'FontSize'] },
        { name: 'basicstyles', items: ['Bold', 'Italic', 'Underline', 'Strike'] },
        { name: 'colors', items: ['TextColor', 'BGColor'] },
        {
          name: 'paragraph',
          items: [
            'NumberedList',
            'BulletedList',
            '-',
            'JustifyLeft',
            'JustifyCenter',
            'JustifyRight',
            'JustifyBlock',
          ],
        },
        { name: 'insert', items: ['Table', 'Smiley', 'SpecialChar', 'PageBreak'] },
        { name: 'tools', items: ['Maximize', 'Source'] },
        { name: 'about', items: ['About'] },
      ],
    });
  });
}

function initCKEditorFormSync() {
  document.querySelectorAll('[type="submit"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (typeof CKEDITOR === 'undefined') return;
      for (var name in CKEDITOR.instances) {
        CKEDITOR.instances[name].updateElement();
      }
    });
  });
}
