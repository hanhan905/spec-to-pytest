const searchForm = document.querySelector('#search-form');
const searchInput = document.querySelector('#post-search');
const postList = document.querySelector('#post-list');
const feedStatus = document.querySelector('#feed-status');

function textElement(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  return element;
}

function actionIcon(kind) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'action-icon');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  const paths = kind === 'like'
    ? ['M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3Z', 'M7 10l4-7a2 2 0 0 1 3 2v5h5a2 2 0 0 1 2 2l-1 7a2 2 0 0 1-2 2H7']
    : ['M21 15a4 4 0 0 1-4 4H8l-5 3 1.5-4A8 8 0 1 1 21 15Z'];
  for (const definition of paths) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', definition);
    svg.appendChild(path);
  }
  return svg;
}

function setStatus(message, {error = false, hidden = false} = {}) {
  feedStatus.textContent = message;
  feedStatus.classList.toggle('error', error);
  feedStatus.hidden = hidden;
}

function renderComments(post, container) {
  container.replaceChildren();
  for (const comment of post.comments) {
    const row = textElement('div', 'comment', '');
    const author = textElement('strong', '', `${comment.author}：`);
    row.append(author, document.createTextNode(comment.text));
    container.appendChild(row);
  }
}

function renderPost(post) {
  const article = document.createElement('article');
  article.className = 'post-card';
  article.dataset.testid = `post-card-${post.id}`;
  article.setAttribute('aria-labelledby', `post-title-${post.id}`);

  const title = textElement('h2', '', post.title);
  title.id = `post-title-${post.id}`;
  const meta = textElement('p', 'post-meta', `作者：${post.author}`);
  const content = textElement('p', 'post-content', post.content);
  article.append(title, meta, content);

  if (post.image_url) {
    const image = document.createElement('img');
    image.className = 'post-image';
    image.src = post.image_url;
    image.alt = `配图：${post.title}`;
    image.loading = 'lazy';
    article.appendChild(image);
  }

  if (post.tags.length) {
    const tags = document.createElement('div');
    tags.className = 'tag-list';
    tags.setAttribute('aria-label', '内容标签');
    for (const tag of post.tags) tags.appendChild(textElement('span', 'tag', tag));
    article.appendChild(tags);
  }

  const actions = document.createElement('div');
  actions.className = 'post-actions';
  const likeButton = textElement('button', 'action-button', '');
  likeButton.type = 'button';
  likeButton.setAttribute('aria-pressed', String(post.liked));
  likeButton.setAttribute('aria-label', `点赞：${post.title}`);
  const likeText = textElement('span', '', `点赞 ${post.like_count}`);
  likeButton.append(actionIcon('like'), likeText);
  const commentCount = textElement('span', 'action-button', '');
  const commentText = textElement('span', '', `评论 ${post.comment_count}`);
  commentCount.append(actionIcon('comment'), commentText);
  commentCount.dataset.testid = `comment-count-${post.id}`;
  actions.append(likeButton, commentCount);
  article.appendChild(actions);

  const comments = document.createElement('div');
  comments.className = 'comment-list';
  comments.dataset.testid = `comments-${post.id}`;
  renderComments(post, comments);
  article.appendChild(comments);

  const form = document.createElement('form');
  form.className = 'comment-form';
  const input = document.createElement('input');
  input.name = 'comment';
  input.maxLength = 100;
  input.required = true;
  input.placeholder = '写下评论，1-100字';
  input.setAttribute('aria-label', `评论内容：${post.title}`);
  const submit = textElement('button', 'primary-button', '提交评论');
  submit.type = 'submit';
  const error = textElement('p', 'comment-error', '');
  error.hidden = true;
  form.append(input, submit);
  article.append(form, error);

  likeButton.addEventListener('click', async () => {
    likeButton.disabled = true;
    try {
      const response = await fetch(`/api/posts/${post.id}/like`, {method: 'POST'});
      if (!response.ok) throw new Error('点赞失败，请稍后重试');
      const payload = await response.json();
      likeText.textContent = `点赞 ${payload.like_count}`;
      likeButton.setAttribute('aria-pressed', String(payload.liked));
    } catch (requestError) {
      error.textContent = requestError.message;
      error.hidden = false;
    } finally {
      likeButton.disabled = false;
    }
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    error.hidden = true;
    submit.disabled = true;
    try {
      const response = await fetch(`/api/posts/${post.id}/comments`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: input.value})
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || '评论提交失败');
      post.comments.push(payload.comment);
      post.comment_count = payload.comment_count;
      commentText.textContent = `评论 ${payload.comment_count}`;
      renderComments(post, comments);
      input.value = '';
    } catch (requestError) {
      error.textContent = requestError.message;
      error.hidden = false;
    } finally {
      submit.disabled = false;
    }
  });

  return article;
}

async function loadPosts() {
  postList.replaceChildren();
  setStatus('正在加载内容…');
  try {
    const query = encodeURIComponent(searchInput.value.trim());
    const response = await fetch(`/api/posts?q=${query}`);
    if (response.status === 401) {
      window.location.assign('/login');
      return;
    }
    if (!response.ok) throw new Error('加载失败，请稍后重试');
    const payload = await response.json();
    if (!payload.posts.length) {
      setStatus(searchInput.value.trim() ? '没有找到匹配内容' : '暂无内容，发布第一条内容吧');
      return;
    }
    setStatus('', {hidden: true});
    for (const post of payload.posts) postList.appendChild(renderPost(post));
  } catch (requestError) {
    setStatus(requestError.message, {error: true});
  }
}

searchForm.addEventListener('submit', (event) => {
  event.preventDefault();
  loadPosts();
});

loadPosts();
