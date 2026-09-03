const form = document.querySelector('#publish-form');
const titleInput = document.querySelector('#title');
const contentInput = document.querySelector('#content');
const imageInput = document.querySelector('#image');
const titleCount = document.querySelector('#title-count');
const contentCount = document.querySelector('#content-count');
const selectedFile = document.querySelector('#selected-file');
const success = document.querySelector('#publish-success');
const error = document.querySelector('#publish-error');
const submit = document.querySelector('#publish-button');

function updateCounts() {
  titleCount.textContent = `${Array.from(titleInput.value.trim()).length}/50`;
  contentCount.textContent = `${Array.from(contentInput.value.trim()).length}/500`;
}

titleInput.addEventListener('input', updateCounts);
contentInput.addEventListener('input', updateCounts);
imageInput.addEventListener('change', () => {
  selectedFile.hidden = !imageInput.files.length;
  selectedFile.textContent = imageInput.files.length ? imageInput.files[0].name : '';
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  success.hidden = true;
  error.hidden = true;
  submit.disabled = true;
  const data = new FormData(form);
  if (!imageInput.files.length) data.delete('image');
  try {
    const response = await fetch('/api/posts', {method: 'POST', body: data});
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join('；')
        : payload.detail;
      throw new Error(detail || '发布失败，请检查表单并重试');
    }
    success.hidden = false;
    success.dataset.postId = payload.id;
  } catch (requestError) {
    error.textContent = requestError.message;
    error.hidden = false;
  } finally {
    submit.disabled = false;
  }
});

updateCounts();
