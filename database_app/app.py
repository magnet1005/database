from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3
import random
import os
import re
from markupsafe import Markup

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

# DB初期化
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute('''
        CREATE TABLE IF NOT EXISTS threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            anon_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        con.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            anon_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(thread_id) REFERENCES threads(id) ON DELETE CASCADE
        )''')
init_db()

# 匿名ID生成
def generate_anon_id():
    return f"{random.randint(0,9999):04d}"

# >>1 のようなリンクを <a> に変換
def convert_reply_links(text):
    def repl(m):
        num = m.group(1)
        return f'<a href="#post-{num}" class="reply-link">&gt;&gt;{num}</a>'
    return Markup(re.sub(r'>>(\d+)', repl, text))

# INDEX
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8" />
<title>匿名掲示板 - スレッド一覧</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Roboto&family=Noto+Sans+JP&display=swap');
  body {
    font-family: "Roboto", "Noto Sans JP", sans-serif;
    max-width: 700px;
    margin: 40px auto;
    color: #202124;
    background: #f8fbff;
    padding: 0 20px;
  }
  h1 {
    font-weight: 600;
    margin-bottom: 25px;
    color: #1a73e8;
    border-bottom: 2px solid #1a73e8;
    padding-bottom: 10px;
  }
  a {
    color: #1a73e8;
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
  .thread {
    padding: 15px 0;
    border-bottom: 1px solid #dbe9ff;
  }
  .title {
    font-size: 18px;
    font-weight: 700;
  }
  .meta {
    font-size: 13px;
    color: #5f6368;
    margin-top: 4px;
  }
  .new-thread-btn {
    display: inline-block;
    margin-bottom: 30px;
    padding: 10px 18px;
    font-weight: 600;
    background-color: #1a73e8;
    color: white;
    border-radius: 5px;
    transition: background-color 0.3s ease;
  }
  .new-thread-btn:hover {
    background-color: #1669c1;
  }
</style>
</head>
<body>
<h1>スレッド一覧</h1>
<a href="/new_thread" class="new-thread-btn">＋ 新しいスレッドを作成</a>
<div>
{% for t in threads %}
  <div class="thread">
    <a class="title" href="/thread/{{ t[0] }}">{{ t[1] }}</a><br>
    <div class="meta">匿名{{ t[2] }} / {{ t[3] }}</div>
  </div>
{% else %}
  <p>スレッドがありません</p>
{% endfor %}
</div>
</body>
</html>
'''

# NEW THREAD
NEW_THREAD_HTML = '''
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8" />
<title>新しいスレッド作成</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Roboto&family=Noto+Sans+JP&display=swap');
  body {
    font-family: "Roboto", "Noto Sans JP", sans-serif;
    max-width: 700px;
    margin: 40px auto;
    color: #202124;
    background: #f8fbff;
    padding: 0 20px;
  }
  h1 {
    font-weight: 600;
    margin-bottom: 25px;
    color: #1a73e8;
    border-bottom: 2px solid #1a73e8;
    padding-bottom: 10px;
  }
  input[type=text] {
    width: 100%;
    padding: 12px 14px;
    font-size: 16px;
    border: 1.5px solid #dbe9ff;
    border-radius: 6px;
  }
  button {
    margin-top: 20px;
    background-color: #1a73e8;
    color: white;
    border: none;
    padding: 12px 20px;
    font-size: 16px;
    font-weight: 600;
    border-radius: 6px;
    cursor: pointer;
  }
  a {
    display: inline-block;
    margin-top: 25px;
    color: #555;
    text-decoration: none;
  }
</style>
</head>
<body>
<h1>新しいスレッド作成</h1>
<form method="POST">
  <input type="text" name="title" placeholder="スレッドタイトル" required />
  <button type="submit">作成</button>
</form>
<a href="/">← スレッド一覧に戻る</a>
</body>
</html>
'''

# THREAD VIEW
THREAD_HTML = '''
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8" />
<title>{{ thread[1] }}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Roboto&family=Noto+Sans+JP&display=swap');
  body {
    font-family: "Roboto", "Noto Sans JP", sans-serif;
    max-width: 700px;
    margin: 40px auto;
    color: #202124;
    background: #f8fbff;
    padding: 0 20px;
  }
  h1 {
    font-weight: 600;
    margin-bottom: 10px;
    color: #1a73e8;
    border-bottom: 2px solid #1a73e8;
    padding-bottom: 10px;
  }
  .meta {
    font-size: 13px;
    color: #5f6368;
    margin-bottom: 20px;
  }
  .post {
    border-bottom: 1px solid #dbe9ff;
    padding: 15px 0;
  }
  .post .anon {
    font-weight: 700;
    color: #3c4043;
  }
  .post .date {
    font-size: 12px;
    color: #80868b;
    margin-left: 12px;
  }
  .post .content {
    margin-top: 8px;
    white-space: pre-wrap;
    line-height: 1.5;
  }
  .reply-link {
    color: #1a73e8;
    text-decoration: none;
    font-weight: bold;
  }
  .reply-link:hover {
    text-decoration: underline;
  }
  form textarea {
    width: 100%;
    height: 110px;
    font-size: 16px;
    padding: 12px 14px;
    border-radius: 6px;
    border: 1.5px solid #dbe9ff;
    resize: vertical;
  }
  form button {
    margin-top: 15px;
    background-color: #1a73e8;
    color: white;
    border: none;
    padding: 12px 20px;
    font-size: 16px;
    font-weight: 600;
    border-radius: 6px;
    cursor: pointer;
  }
  a {
    display: inline-block;
    margin-top: 30px;
    color: #555;
    text-decoration: none;
  }
</style>
</head>
<body>
<h1>{{ thread[1] }}</h1>
<div class="meta">スレッド作成者: 匿名{{ thread[2] }} / {{ thread[3] }}</div>

<div id="post-list">
{% for p in posts %}
  <div class="post" id="post-{{ p.id }}">
    <span class="anon">{{ p.id }}. 匿名{{ p.anon_id }}</span>
    <span class="date">{{ p.created_at }}</span>
    <div class="content">{{ p.content|safe }}</div>
  </div>
{% else %}
  <p>まだ投稿はありません。</p>
{% endfor %}
</div>

<form method="POST">
  <textarea name="content" placeholder="コメントを書く" required></textarea>
  <button type="submit">投稿する</button>
</form>
<a href="/">← スレッド一覧に戻る</a>

<script>
async function fetchPosts() {
  const res = await fetch(location.pathname + "/posts");
  const data = await res.json();
  const postList = document.getElementById("post-list");
  postList.innerHTML = "";

  data.posts.forEach(post => {
    const div = document.createElement("div");
    div.className = "post";
    div.id = `post-${post.id}`;
    div.innerHTML = `
      <span class="anon">${post.id}. 匿名${post.anon_id}</span>
      <span class="date">${post.created_at}</span>
      <div class="content">${post.content}</div>
    `;
    postList.appendChild(div);
  });
}
setInterval(fetchPosts, 5000);
</script>
</body>
</html>
'''

# 各ルート処理
@app.route('/')
def index():
    con = sqlite3.connect(DB_PATH)
    threads = con.execute('SELECT id, title, anon_id, created_at FROM threads ORDER BY created_at DESC').fetchall()
    con.close()
    return render_template_string(INDEX_HTML, threads=threads)

@app.route('/new_thread', methods=['GET', 'POST'])
def new_thread():
    if request.method == 'POST':
        title = request.form['title']
        anon_id = generate_anon_id()
        con = sqlite3.connect(DB_PATH)
        cur = con.execute('INSERT INTO threads (title, anon_id) VALUES (?, ?)', (title, anon_id))
        con.commit()
        thread_id = cur.lastrowid
        con.close()
        return redirect(f'/thread/{thread_id}')
    return render_template_string(NEW_THREAD_HTML)

@app.route('/thread/<int:thread_id>', methods=['GET', 'POST'])
def thread(thread_id):
    con = sqlite3.connect(DB_PATH)
    if request.method == 'POST':
        content = request.form['content']
        anon_id = generate_anon_id()
        con.execute('INSERT INTO posts (thread_id, content, anon_id) VALUES (?, ?, ?)', (thread_id, content, anon_id))
        con.commit()

    thread = con.execute('SELECT id, title, anon_id, created_at FROM threads WHERE id=?', (thread_id,)).fetchone()
    posts_raw = con.execute(
        'SELECT id, content, anon_id, created_at FROM posts WHERE thread_id=? ORDER BY created_at',
        (thread_id,)
    ).fetchall()
    con.close()

    if thread is None:
        return "スレッドが見つかりません", 404

    posts = [
        {"id": row[0], "content": convert_reply_links(row[1]), "anon_id": row[2], "created_at": row[3]}
        for row in posts_raw
    ]

    return render_template_string(THREAD_HTML, thread=thread, posts=posts)

@app.route('/thread/<int:thread_id>/posts')
def get_posts(thread_id):
    con = sqlite3.connect(DB_PATH)
    posts_raw = con.execute(
        'SELECT id, content, anon_id, created_at FROM posts WHERE thread_id=? ORDER BY created_at',
        (thread_id,)
    ).fetchall()
    con.close()
    posts = [
        {
            "id": row[0],
            "content": str(convert_reply_links(row[1])),
            "anon_id": row[2],
            "created_at": row[3]
        }
        for row in posts_raw
    ]
    return jsonify({"posts": posts})

if __name__ == '__main__':
    app.run(debug=True)
