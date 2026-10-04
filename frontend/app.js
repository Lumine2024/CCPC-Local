"use strict";
const $ = (q, root = document) => root.querySelector(q);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const duration = seconds => {
  seconds = Math.max(0, Math.floor(seconds));
  return [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60]
    .map(n => String(n).padStart(2, "0")).join(":");
};
const pending = verdict => ["Queued", "Compiling", "Running"].includes(verdict);
const verdictName = v => ({
  Queued: "等待判题", Compiling: "正在编译", Running: "正在运行", "Judge Error": "评测系统错误"
}[v] || v);
const verdictClass = v => v === "AC" ? "success" : pending(v) ? "pending" : "failure";
let state, sessionId = null, refreshBusy = false, renderGeneration = 0, routeKey = "", filter = "", receivedAt = 0;
const markdownCache = new Map();
const route = () => (location.hash.slice(1) || "problems").split("/");
const api = async (path, body) => {
  const response = await fetch(path, {
    credentials: "same-origin", ...(body !== undefined ? {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state?.csrf || "" },
      body: JSON.stringify(body)
    } : {})
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
};
function showError(message) {
  const node = $("#error");
  node.textContent = message;
  node.hidden = !message;
}
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  setTimeout(() => $("#toast").hidden = true, 2500);
}
function phase() {
  return !state.session ? "尚未开始" : state.board.ended ? "比赛已结束" : state.board.frozen ? "四小时封榜" : "比赛进行中";
}
function active() {
  return Boolean(state?.session && !state.board.ended);
}
function localElapsed() {
  return state?.session ? state.board.elapsed + (performance.now() - receivedAt) / 1000 : 0;
}
function updateClock() {
  if (!state) return;
  if ($("#elapsed-clock")) $("#elapsed-clock").textContent = duration(Math.min(localElapsed(), state.contest.duration));
  if ($("#remaining-clock")) $("#remaining-clock").textContent = `剩余 ${duration(state.contest.duration - localElapsed())}`;
}
function sidebar() {
  const currentName = $("#vp-name")?.value || "我的 VP 队伍";
  const oldFocus = document.activeElement?.id;
  const c = state.contest, b = state.board;
  $("#sidebar").innerHTML = `<section class="panel"><div class="sidebar-title">比赛信息</div><div class="contest-summary"><div><div class="phase">${phase()}</div><div class="clock" id="elapsed-clock">${duration(Math.min(b.elapsed, c.duration))}</div><div class="remaining" id="remaining-clock">剩余 ${duration(c.duration - b.elapsed)}</div></div><div class="progress"><span style="width:${Math.min(100, b.elapsed / c.duration * 100)}%"></span></div><dl class="metadata"><dt>比赛时长</dt><dd>${c.duration / 60} 分钟</dd><dt>历史队伍</dt><dd>${c.historical_teams}</dd><dt>公开阈值</dt><dd>${b.threshold} 支队伍</dd><dt>封榜时间</dt><dd>04:00:00</dd><dt>计分模式</dt><dd>ICPC</dd></dl></div></section>
    <section class="panel vp-panel"><div class="sidebar-title">→ Virtual participation</div><div class="panel-body">${active() ? `<p><strong>${esc(state.session.name)}</strong></p><p class="hint">刷新或重启后继续计时。赛时提交不公开耗时与内存。</p><a href="#submit" class="own-status">提交代码 →</a>` : `<p class="hint">${state.session ? "本场 VP 已结束，可查看最终结果，或开启新的比赛。" : "与历史队伍同时起跑，体验 CCPC 新榜单机制。"}</p><form id="vp-form" class="vp-form"><input id="vp-name" aria-label="队伍名" maxlength="100" value="${esc(currentName)}" required><button class="primary" type="submit">${state.session ? "重新 VP" : "开始 VP"}</button></form>${state.session ? '<p><a href="#final">查看最终结果 →</a></p>' : ""}`}</div></section>
    <section class="panel rules-panel"><div class="sidebar-title">榜单规则</div><div class="panel-body"><div class="rule-note">四小时前，至少 <strong>${b.threshold}</strong> 队通过的题目才公开人数与逐队详情。其余通过计入“其他”。<br><br>四小时起公开所有题目的四小时快照，随后封榜。本人判定继续更新。</div>${b.pending ? `<p class="hint">当前快照仍有 ${b.pending} 条待判提交。</p>` : ""}</div></section>
    ${state.sessions.length ? `<section class="panel archive-panel"><div class="sidebar-title">本地会话</div><div class="panel-body"><select id="session-select" class="session-select" aria-label="选择历史 VP 会话">${state.sessions.map(s => `<option value="${s.id}" ${s.id === state.session?.id ? "selected" : ""}>${esc(s.name)} · ${new Date(s.started * 1000).toLocaleDateString()} ${s.ended ? "已结束" : "进行中"}</option>`).join("")}</select></div></section>` : ""}`;
  if (oldFocus === "vp-name") $("#vp-name")?.focus();
  $("#vp-form")?.addEventListener("submit", async event => {
    event.preventDefault(); const button = $("button", event.target); button.disabled = true;
    try {
      const result = await api("/api/vp", { name: $("#vp-name").value });
      sessionId = result.session_id;
      location.hash = "problems";
      routeKey = "";
      await refresh();
      toast("VP 已开始，祝比赛顺利。");
    }
    catch (error) {
      showError(error.message);
      button.disabled = false;
    }
  });
  $("#session-select")?.addEventListener("change", async event => {
    sessionId = event.target.value;
    routeKey = "";
    location.hash = "problems";
    await refresh();
  });
}
function problemList() {
  return `<section class="panel"><div class="panel-title"><span>Problems · 题目列表</span><small>${state.problems.length} problems</small></div><div class="table-scroll"><table><thead><tr><th class="problem-id">#</th><th>题目</th><th class="limits">限制</th><th>我的状态</th><th class="problem-stats">通过队伍</th></tr></thead><tbody>${state.problems.map(p => `<tr class="${p.own?.solved ? "solved-row" : ""}"><td class="problem-id"><a href="#problem/${p.id}">${p.id}</a></td><td class="problem-name"><a href="#problem/${p.id}">${esc(p.name)}</a></td><td class="limits">${p.time_limit_ms / 1000} s / ${p.memory_limit_mb} MiB</td><td class="own-status ${p.own?.solved ? "success" : ""}">${p.own?.solved ? "已通过" : p.own?.wrong ? `尝试 ${p.own.wrong} 次` : "—"}</td><td class="problem-stats ${state.board.counts[p.id] === null ? "hidden-count" : ""}">${state.board.counts[p.id] ?? "?"}</td></tr>`).join("")}</tbody></table></div></section><p class="hint">“?” 表示未达到公开阈值。题目始终可阅读和提交；公开统计使用当前榜单快照。</p>`;
}
function submitForm(pid) {
  const p = state.problems.find(x => x.id === pid) || state.problems[0];
  return `<section class="panel"><div class="panel-title">Submit code · 提交代码</div><div class="panel-body">${!active() ? '<div class="callout">请在右侧开始 VP；比赛结束后不接受赛时提交。</div>' : state.board.frozen ? '<div class="callout">榜单已封，您的提交会正常判定并更新个人记录。</div>' : ""}<form id="submit-form"><div class="form-grid"><div class="form-row"><label for="submit-problem">题目</label><select id="submit-problem">${state.problems.map(x => `<option value="${x.id}" ${x.id === p.id ? "selected" : ""}>${x.id} · ${esc(x.name)}</option>`).join("")}</select></div><div class="form-row"><label for="submit-language">语言</label><select id="submit-language">${state.languages.map(l => `<option value="${l.id}">${esc(l.name)}</option>`).join("")}</select></div></div><div class="form-row"><label for="source-file">选择源文件 <span class="hint">或在下方粘贴代码</span></label><input id="source-file" type="file" accept=".cpp,.cc,.cxx,.py,.txt"></div><div class="form-row"><label for="source-code">源代码</label><textarea id="source-code" class="source-editor" spellcheck="false" placeholder="在这里粘贴代码…" required></textarea></div><div class="form-actions"><button id="send-code" class="primary" ${active() ? "" : "disabled"}>提交代码</button><span class="hint">最多 256 KiB · 使用全部样例和隐藏数据判题</span></div></form></div></section>`;
}
function wireSubmit() {
  const editor = $("#source-code");
  if (!editor) return;
  const draftKey = () => `ccpc-draft:${state.session?.id || "lobby"}:${$("#submit-problem").value}`;
  editor.value = sessionStorage.getItem(draftKey()) || "";
  editor.addEventListener("input", () => sessionStorage.setItem(draftKey(), editor.value));
  editor.addEventListener("keydown", event => {
    if (event.key === "Tab") {
      event.preventDefault();
      const start = editor.selectionStart, end = editor.selectionEnd;
      editor.setRangeText("\t", start, end, "end");
      editor.dispatchEvent(new Event("input"));
    }
  });
  $("#submit-problem").addEventListener("change", () => {
    editor.value = sessionStorage.getItem(draftKey()) || "";
  });
  $("#source-file").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 256 * 1024) {
      showError("源文件超过 256 KiB");
      return;
    } editor.value = await file.text();
    if (file.name.endsWith(".py")) $("#submit-language").value = "python";
    editor.dispatchEvent(new Event("input"));
  });
  $("#submit-form").addEventListener("submit", async event => {
    event.preventDefault();
    const button = $("#send-code");
    button.disabled = true;
    button.textContent = "正在接收…";
    try {
      const result = await api("/api/submissions", {
        session_id: state.session?.id,
        problem: $("#submit-problem").value,
        language: $("#submit-language").value,
        source: editor.value
      });
      location.hash = `submission/${result.id}`;
      toast(`提交 #${result.id} 已进入判题队列`);
      await refresh();
    }
    catch (error) {
      showError(error.message);
      button.disabled = !active();
      button.textContent = "提交代码";
    }
  });
}
function submissions() {
  const rows = state.submissions;
  if (!rows.length) return `<section class="panel"><div class="panel-title">My submissions · 我的提交</div><div class="empty"><strong>还没有提交记录</strong>${active() ? '<a href="#submit">提交第一份代码 →</a>' : "开始 VP 后，提交结果将在这里显示。"}</div></section>`;
  const ended = state.board.ended;
  return `<section class="panel"><div class="panel-title"><span>My submissions · 我的提交</span><small>${rows.length} submissions</small></div><div class="table-scroll"><table class="submission-table"><thead><tr><th>ID</th><th>提交时间</th><th>题目</th><th>语言</th><th>结果</th>${ended ? "<th>耗时</th><th>内存</th>" : ""}</tr></thead><tbody>${rows.map(s => `<tr><td class="submission-id"><a href="#submission/${s.id}">${s.id}</a></td><td class="date">${esc(new Date(s.received * 1000).toLocaleString())}<br>+${duration(s.elapsed)}</td><td><a href="#problem/${s.problem}">${s.problem} · ${esc(s.name)}</a></td><td>${s.language === "cpp" ? "C++" : "Python 3"}</td><td class="verdict ${verdictClass(s.verdict)}">${verdictName(s.verdict)}</td>${ended ? `<td>${s.time_ms ?? "—"} ms</td><td>${s.memory_kb ?? "—"} KiB</td>` : ""}</tr>`).join("")}</tbody></table></div></section>`;
}
function boardTable() {
  const b = state.board;
  const rows = b.rows.filter(r => r.name.toLowerCase().includes(filter.toLowerCase()));
  const others = b.visible.length < state.problems.length;
  return `<table class="board"><thead><tr><th>#</th><th class="team">队伍</th><th>通过</th><th>罚时</th>${b.visible.map(pid => `<th><a href="#problem/${pid}">${pid}</a><br><small>${b.counts[pid]}</small></th>`).join("")}${others ? "<th>其他</th>" : ""}</tr></thead><tbody>${rows.map(r => `<tr class="${r.local ? "local-row" : ""}" ${r.local ? 'id="my-team"' : ""}><td>${r.rank}</td><td class="team">${esc(r.name)}${r.local ? '<span class="badge">VP</span>' : ""}</td><td><strong>${r.solved}</strong></td><td>${r.penalty}</td>${b.visible.map(pid => { const c = r.cells[pid]; return `<td class="${c?.solved ? "success" : c?.wrong ? "failure" : ""}">${c?.solved ? `+${c.wrong || ""}<span class="cell-time">${duration(c.at).slice(0, 5)}</span>` : c?.wrong ? `-${c.wrong}` : ""}</td>`; }).join("")}${others ? `<td>${r.other ? `其他${r.other}题` : "—"}</td>` : ""}</tr>`).join("")}</tbody></table>`;
}
function scoreboard() {
  const b = state.board;
  return `${b.pending ? `<div class="callout">快照中仍有 ${b.pending} 条提交尚未完成判题；按接收时间归属成绩。</div>` : ""}<section class="panel"><div class="panel-title"><span>Standings · ${b.final ? "最终结果" : b.frozen ? "四小时封榜" : b.ended ? "结束快照" : "比赛榜单"}</span><small>快照 ${duration(b.snapshot)}</small></div><div class="board-tools"><input id="team-filter" aria-label="搜索队伍" placeholder="搜索队伍名…" value="${esc(filter)}"><button id="locate-team" ${state.session ? "" : "disabled"}>定位我的队伍</button>${b.ended && !b.final ? '<a href="#final">查看最终结果 →</a>' : b.final ? '<a href="#board">返回封榜视图 →</a>' : ""}</div><div class="table-scroll" id="board-table">${boardTable()}</div><div class="board-legend">+ 已通过 · +k 首次通过前失败 k 次 · -k 尚未通过 · 罚时单位：分钟 ${b.visible.length < state.problems.length ? "· 隐藏题汇总在“其他”" : ""}</div></section>`;
}
function wireBoard() {
  $("#team-filter").addEventListener("input", event => {
    filter = event.target.value;
    $("#board-table").innerHTML = boardTable();
  });
  $("#locate-team").addEventListener("click", () => {
    filter = "";
    $("#team-filter").value = "";
    $("#board-table").innerHTML = boardTable();
    $("#my-team")?.scrollIntoView({ block: "center", behavior: "smooth" });
  });
}
function renderMarkdown(markdown, pid) {
  const math = [];
  // Protect LaTeX from Markdown's backslash escaping; code fences are untouched.
  const protectedMarkdown = markdown.split(/(^```[^\n]*\n[\s\S]*?^```\s*$)/gm).map((part, i) => i % 2 ? part : part.replace(/\$\$[\s\S]*?\$\$|\$[^\n$]+\$/g, m => { math.push(m); return `CCPCMATHPLACEHOLDER${math.length - 1}END`; })).join("");
  let html = DOMPurify.sanitize(marked.parse(protectedMarkdown));
  html = html.replace(/CCPCMATHPLACEHOLDER(\d+)END/g, (_, n) => esc(math[Number(n)]));
  const holder = document.createElement("div"); holder.innerHTML = html;
  const sampleGroups = new Map();
  holder.querySelectorAll("pre > code").forEach(code => {
    const type = code.className.match(/language-(input|output)(\d*)$/); if (!type) return;
    const key = type[2] || "1", kind = type[1];
    const pre = code.parentNode, block = document.createElement("div");
    block.className = "sample-block";
    const head = document.createElement("div");
    head.className = "sample-head";
    const label = document.createElement("span");
    label.textContent = `${kind} ${key}`;
    const button = document.createElement("button");
    button.className = "copy-button"; button.type = "button"; button.textContent = "复制";
    head.append(label, button);
    block.append(head, pre.cloneNode(true));
    const raw = code.textContent;
    button.addEventListener("click", async () => { try { await navigator.clipboard.writeText(raw); button.textContent = "已复制"; setTimeout(() => button.textContent = "复制", 1600); } catch { const range = document.createRange(); range.selectNodeContents($("pre", block)); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); toast("请按 Ctrl+C 复制已选中的样例。"); } });
    let group = sampleGroups.get(key);
    if (!group) {
      group = document.createElement("div");
      group.className = "samples";
      pre.replaceWith(group);
      sampleGroups.set(key, group);
    } else pre.remove();
    if (kind === "input") group.prepend(block);
    else group.append(block);
  });
  holder.querySelectorAll("img").forEach(img => {
    const src = img.getAttribute("src") || "";
    img.src = `/api/problems/${encodeURIComponent(pid)}/assets/${src.split("/").map(encodeURIComponent).join("/")}`;
    img.loading = "lazy";
  });
  holder.querySelectorAll("a").forEach(a => {
    a.rel = "noopener noreferrer";
    a.target = "_blank";
  });
  renderMathInElement(holder, {
    delimiters: [{
      left: "$$",
      right: "$$",
      display: true
    }, {
      left: "$",
      right: "$",
      display: false
    }],
    throwOnError: false,
    trust: false
  });
  return holder;
}
async function renderRoute(force = false) {
  if (!state) return;
  const [page, param] = route(), key = location.hash || "#problems";
  document.querySelectorAll(".tabs a").forEach(a =>
    a.classList.toggle("active", a.dataset.tab === (page === "problem" ? "problems" : page === "submission" ? "submissions" : page === "final" ? "board" : page)));
  if (!force && routeKey === key && ["problem", "submit"].includes(page)) {
    if ($("#send-code")) $("#send-code").disabled = !active();
    return;
  }
  const filterFocus = document.activeElement?.id === "team-filter" ? [document.activeElement.selectionStart, document.activeElement.selectionEnd] : null;
  routeKey = key;
  const generation = ++renderGeneration, content = $("#content");
  if (page === "problems") content.innerHTML = problemList();
  else if (page === "submit") {
    content.innerHTML = submitForm(param);
    wireSubmit();
  }
  else if (page === "submissions") content.innerHTML = submissions();
  else if (page === "board" || page === "final") {
    content.innerHTML = scoreboard();
    wireBoard();
    if (filterFocus) {
      $("#team-filter").focus();
      $("#team-filter").setSelectionRange(...filterFocus);
    }
  }
  else if (page === "problem") {
    const p = state.problems.find(p => p.id === param);
    if (!p) {
      content.innerHTML = '<div class="empty">题目不存在</div>';
      return;
    }
    content.innerHTML = '<div class="empty">正在读取题面…</div>';
    try {
      if (!markdownCache.has(param)) markdownCache.set(param, await api(`/api/problems/${encodeURIComponent(param)}`));
      if (generation !== renderGeneration) return;
      content.innerHTML = `<div class="problem-header"><h2>${p.id} · ${esc(p.name)}</h2><p>时间限制：${p.time_limit_ms / 1000} 秒</p><p>内存限制：${p.memory_limit_mb} MiB</p></div><article class="statement" id="statement"></article><div class="mobile-submit">${submitForm(param)}</div>`;
      $("#statement").append(renderMarkdown(markdownCache.get(param).markdown, param));
      wireSubmit();
    } catch (error) {
      showError(error.message);
      routeKey = "";
    }
  } else if (page === "submission") {
    try {
      const sub = await api(`/api/submissions/${encodeURIComponent(param)}`);
      if (generation !== renderGeneration) return;
      content.innerHTML = `<section class="panel"><div class="panel-title"><span>Submission #${sub.id}</span><a href="#submissions">全部提交 →</a></div><div class="panel-body"><dl class="detail-grid"><dt>题目</dt><dd><a href="#problem/${sub.problem}">${sub.problem} · ${esc(sub.name)}</a></dd><dt>提交时间</dt><dd>${esc(new Date(sub.received * 1000).toLocaleString())} · +${duration(sub.elapsed)}</dd><dt>语言</dt><dd>${sub.language === "cpp" ? "C++" : "Python 3"}</dd><dt>结果</dt><dd class="verdict ${verdictClass(sub.verdict)}">${verdictName(sub.verdict)}</dd>${"time_ms" in sub ? `<dt>耗时 / 内存</dt><dd>${sub.time_ms ?? "—"} ms / ${sub.memory_kb ?? "—"} KiB</dd>` : ""}</dl>${sub.message ? `<pre class="source-view">${esc(sub.message)}</pre>` : ""}<h3>提交源码</h3><pre class="source-view">${esc(sub.source)}</pre></div></section>`;
    } catch (error) {
      showError(error.message);
    }
  } else {
    content.innerHTML = '<div class="empty">页面不存在 <a href="#problems">返回首页</a></div>';
  }
}
async function refresh() {
  if (refreshBusy) return;
  refreshBusy = true;
  try {
    const query = new URLSearchParams();
    if (sessionId) query.set("session_id", sessionId);
    if (route()[0] === "final") query.set("final", "1");
    const next = await api(`/api/state?${query}`);
    state = next;
    sessionId = state.session?.id || null;
    receivedAt = performance.now();
    $("#contest-title").textContent = state.contest.title;
    $("#connection-label").textContent = "本机服务在线";
    $("#nav-phase").textContent = phase();
    showError("");
    sidebar();
    await renderRoute();
  } catch (error) {
    showError(error.message);
    $("#connection-label").textContent = "连接中断";
    if (route()[0] === "final" && !state?.board.ended) location.hash = "board";
  }
  finally {
    refreshBusy = false;
  }
}
window.addEventListener("hashchange", () => {
  routeKey = "";
  showError("");
  if (state && route()[0] !== "final") renderRoute(true);
  refresh();
});
refresh();
setInterval(refresh, 4000);
setInterval(updateClock, 1000);
