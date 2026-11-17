const $ = (s) => document.querySelector(s);

const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

async function getJSON(url) {
  const res = await fetch(url, { cache: "no-store" });
  return res.json();
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return res.json();
}

const state = { convId: "", conv: null, workflow: "", parsed: null, busy: false,
                selectWF: false, wfData: null, genBusy: false, generations: [],
                runtime: null, settings: null, backups: [], previewGid: "",
                previewIndex: 0, previewZoom: 1, lastError: "" };

// ---------------------------------------------------------------- 提示 / 错误
function toast(message, type, actionLabel, action, timeout) {
  const box = $("#toasts");
  if (!box) return;
  const el = document.createElement("div");
  el.className = "toast " + (type || "ok");
  el.innerHTML = `<span class="t-dot"></span><span class="t-main">${esc(message)}</span>`;
  if (actionLabel && action) {
    const act = document.createElement("button");
    act.className = "t-act";
    act.textContent = actionLabel;
    act.addEventListener("click", action);
    el.appendChild(act);
  }
  const close = document.createElement("button");
  close.className = "t-x";
  close.textContent = "×";
  close.addEventListener("click", () => el.remove());
  el.appendChild(close);
  box.appendChild(el);
  const ttl = timeout === undefined ? (type === "error" ? 9000 : 3500) : timeout;
  if (ttl > 0) setTimeout(() => el.remove(), ttl);
  return el;
}

function postClientLog(level, message, detail) {
  try {
    fetch("/api/client-log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level, message: String(message || "").slice(0, 600),
                            detail: detail || {}, url: location.pathname }),
      keepalive: true,
    }).catch(() => {});
  } catch (e) {
    /* 日志上报失败不能影响主流程 */
  }
}

function showError(message, hint, detail) {
  const text = [message || "出错了", hint].filter(Boolean).join(" · ");
  state.lastError = text;
  $("#errorText").textContent = text;
  $("#errorBanner").hidden = false;
  toast(text, "error", "日志", () => openLogs(), 9000);
  postClientLog("error", message || "未知错误", detail || (hint ? { hint } : {}));
}

function hideError() {
  $("#errorBanner").hidden = true;
  state.lastError = "";
}

// ---------------------------------------------------------------- 顶部状态
function fmtDuration(sec) {
  sec = Number(sec || 0);
  if (sec < 60) return sec.toFixed(0) + " 秒";
  if (sec < 3600) return Math.floor(sec / 60) + " 分 " + Math.round(sec % 60) + " 秒";
  return Math.floor(sec / 3600) + " 时 " + Math.floor((sec % 3600) / 60) + " 分";
}

function renderRuntime(rt) {
  if (!rt) return;
  $("#rtUptime").textContent = "已运行 " + fmtDuration(rt.uptime_sec);
  const gen = (rt.active || {}).generate;
  const chat = (rt.active || {}).chat;
  let task = "空闲";
  let busyType = "";
  if (gen) { task = "出图中 · " + (gen.stage || "准备"); busyType = "busy"; }
  else if (chat) { task = "对话中 · " + (chat.stage || "生成"); busyType = "busy"; }
  const dot = $("#rtDot");
  dot.className = "rt-dot " + (rt.last_error && !busyType ? "bad" : busyType);
  $("#rtTask").textContent = task;
  const c = rt.counters || {};
  $("#rtBusy").textContent = `对话 ${c.chat || 0} · 出图 ${c.generate || 0}`;
  const tail = (rt.log_tail || [])[0];
  $("#rtEvent").textContent = tail
    ? `${tail.level.toUpperCase()} · ${tail.message}`
    : "—";
  $("#rtEvent").title = tail ? `${tail.ts} [${tail.scope}] ${tail.message}` : "";
}

async function loadRuntime() {
  try {
    const data = await getJSON("/api/runtime");
    if (!data.ok) return;
    state.runtime = data.runtime;
    renderRuntime(data.runtime);
  } catch (e) {
    const dot = $("#rtDot");
    if (dot) dot.className = "rt-dot bad";
  }
}

async function loadStatus() {
  const s = await getJSON("/api/status");
  const ollama = $("#chip-ollama");
  ollama.className = "chip " + (s.ollama.running ? "ok" : "bad");
  ollama.textContent = s.ollama.running
    ? `Ollama 在运行${s.ollama.version ? " " + s.ollama.version : ""}`
    : "Ollama 未运行（请先开 Ollama 桌面版）";

  const model = $("#chip-model");
  model.className = "chip " + (s.ollama.model_registered ? "ok" : "bad");
  model.textContent = s.ollama.model_registered
    ? `模型 ${s.ollama.target_model} 已注册`
    : `模型 ${s.ollama.target_model} 未注册`;

  const comfy = $("#chip-comfy");
  comfy.className = "chip " + (s.comfyui.running ? "ok" : "");
  comfy.textContent = s.comfyui.running ? "ComfyUI 在运行" : "ComfyUI 未启动";

  const vram = s.vram || {};
  const gpu = vram.gpu || {};
  const chip = $("#chip-vram");
  if (gpu.ok) {
    const need = vram.min_free_mb || 4000;
    chip.className = "chip " + (gpu.free_mb >= need ? "ok" : "bad");
    chip.textContent = `显存 ${gpu.used_mb}/${gpu.total_mb} MB（空闲 ${gpu.free_mb}）`;
    chip.title = `自动管理：${vram.auto_manage ? "开" : "关"}；出图前要求空闲 ≥ ${need} MB`;
  } else {
    chip.className = "chip bad";
    chip.textContent = "显存读不到（nvidia-smi 不可用）";
    chip.title = gpu.error || "";
  }
}

// ---------------------------------------------------------------- 工作流
async function loadWorkflows(preferredName) {
  const data = await getJSON("/api/workflows");
  const sel = $("#wf");
  if (!data.workflows.length) {
    sel.innerHTML = `<option value="">（工作流目录为空）</option>`;
    $("#wfinfo").textContent = "目录：" + (data.dir || "未配置");
    $("#wfdetail").innerHTML = `<div class="muted small">还没有工作流，点“导入”加一个。</div>`;
    $("#wfmap").innerHTML = "";
    return;
  }
  sel.innerHTML = data.workflows.map((w) => {
    const mark = w.source === "workbench" ? " ·导入" : "";
    const tail = w.ok ? ` · ${w.format === "api" ? "API" : "UI"}` : " · 解析失败";
    return `<option value="${esc(w.name)}">${esc(w.name + mark + tail)}</option>`;
  }).join("");
  const wanted = preferredName && data.workflows.some((w) => w.name === preferredName)
    ? preferredName
    : (data.default && data.workflows.some((w) => w.name === data.default)
      ? data.default : data.workflows[0].name);
  sel.value = wanted;
  const counts = data.counts || {};
  $("#wfinfo").textContent =
    `${counts.all || data.workflows.length} 个工作流（ComfyUI ${counts.comfyui || 0} · 导入 ${counts.workbench || 0}）`;
  await selectWorkflow(wanted);
}

async function selectWorkflow(name) {
  state.workflow = name;
  if (!name) return;
  const data = await getJSON("/api/workflow?name=" + encodeURIComponent(name));
  state.parsed = data.parsed || null;
  state.wfData = data;
  renderModel(data);
  renderWorkflowDetail(data);
  renderMapping(data);
  await loadInjection();
}

function renderWorkflowDetail(data) {
  const box = $("#wfdetail");
  if (!data.ok) {
    box.innerHTML = `<div class="bad">${esc(data.message || "解析失败")}</div>`;
    return;
  }
  const p = data.parsed || {};
  const sampler = p.sampler || {};
  const latent = p.latent || {};
  const pos = p.positive || {};
  const neg = p.negative || {};
  const clip = (s, n) => {
    const t = String(s || "").replace(/\n/g, " ");
    return t.length > n ? t.slice(0, n) + "…" : t;
  };
  const srcTag = (item) => (item.source === "manual"
    ? `<span class="pill warn">人工映射</span>`
    : `<span class="pill ok">连线判定</span>`);

  let html = "";
  html += `<div class="wf-line"><span class="k">格式 / 来源</span><span class="v">${esc(p.format === "api" ? "API Prompt" : "UI Workflow")} · ${esc(data.source === "workbench" ? "工作台库（可映射）" : "ComfyUI 目录（只读）")}</span></div>`;
  html += `<div class="wf-line"><span class="k">Checkpoint</span><span class="v">${esc((p.checkpoint || {}).name || "未找到")}</span></div>`;
  html += `<div class="wf-line"><span class="k">正向节点</span><span class="v">${esc((pos.node_ids || []).join("、") || "未判定")} ${srcTag(pos)}</span></div>`;
  if (pos.text) html += `<div class="wf-textpre">${esc(clip(pos.text, 260))}</div>`;
  html += `<div class="wf-line"><span class="k">负向节点</span><span class="v">${esc((neg.node_ids || []).join("、") || "未判定")} ${srcTag(neg)}</span></div>`;
  if (neg.text) html += `<div class="wf-textpre">${esc(clip(neg.text, 260))}</div>`;
  if ((p.loras || []).length) {
    p.loras.forEach((l) => {
      html += `<div class="wf-line"><span class="k">LoRA</span><span class="v">${esc(l.name)} · model ${esc(l.strength_model)} / clip ${esc(l.strength_clip)} · 节点 ${esc(l.node_id)}</span></div>`;
    });
  } else {
    html += `<div class="wf-line"><span class="k">LoRA</span><span class="v">无</span></div>`;
  }
  const bits = [];
  if (sampler.sampler_name) bits.push(esc(sampler.sampler_name));
  if (sampler.scheduler) bits.push(esc(sampler.scheduler));
  if (sampler.steps != null) bits.push(`${esc(sampler.steps)} 步`);
  if (sampler.cfg != null) bits.push(`CFG ${esc(sampler.cfg)}`);
  if (sampler.seed != null) bits.push(`seed ${esc(sampler.seed)}`);
  if (sampler.denoise != null) bits.push(`denoise ${esc(sampler.denoise)}`);
  html += `<div class="wf-line"><span class="k">采样</span><span class="v">${bits.join(" · ") || "未找到 KSampler"}</span></div>`;
  if (latent.width) {
    html += `<div class="wf-line"><span class="k">分辨率</span><span class="v">${esc(latent.width)}×${esc(latent.height)} · batch ${esc(latent.batch)}</span></div>`;
  }
  (p.warnings || []).forEach((w) => {
    html += `<div class="wf-line"><span class="k">提示</span><span class="v" style="color:var(--warn)">${esc(w)}</span></div>`;
  });
  box.innerHTML = html;
}

function nodeOptions(list, current) {
  const opts = [`<option value="">（自动）</option>`];
  (list || []).forEach((item) => {
    const sel = String(item.id) === String(current || "") ? " selected" : "";
    opts.push(`<option value="${esc(item.id)}"${sel}>节点 ${esc(item.id)} · ${esc(item.type)} · ${esc(item.preview || "")}</option>`);
  });
  return opts.join("");
}

function renderMapping(data) {
  const box = $("#wfmap");
  if (!data.ok) { box.innerHTML = ""; return; }
  const cand = data.candidates || { text_nodes: [], samplers: [] };
  const map = data.mapping || {};
  if (!cand.text_nodes.length && !cand.samplers.length) {
    box.innerHTML = `<div class="muted">这个工作流里没有可映射的文本 / 采样节点。</div>`;
    return;
  }
  box.innerHTML = `
    <div class="hint" style="margin:0 0 8px">人工映射（可选，覆盖按连线的自动判定）</div>
    <div class="map-row"><span class="k">正向节点</span><select id="wfPosMap">${nodeOptions(cand.text_nodes, map.positive_node)}</select></div>
    <div class="map-row"><span class="k">负向节点</span><select id="wfNegMap">${nodeOptions(cand.text_nodes, map.negative_node)}</select></div>
    <div class="map-row"><span class="k">采样节点</span><select id="wfSamplerMap">${nodeOptions(cand.samplers, map.sampler_node)}</select></div>
    <div class="map-actions">
      <button class="mini-btn" id="wfMapSave">保存映射</button>
      ${data.source === "workbench" ? '<button class="mini-btn" id="wfDelete">删除这个工作流</button>' : ""}
    </div>`;
  $("#wfMapSave").addEventListener("click", saveMapping);
  const del = $("#wfDelete");
  if (del) del.addEventListener("click", deleteWorkflow);
}

async function saveMapping() {
  if (!state.workflow) return;
  const res = await postJSON("/api/workflows/mapping", {
    name: state.workflow,
    positive_node: $("#wfPosMap").value,
    negative_node: $("#wfNegMap").value,
    sampler_node: $("#wfSamplerMap").value,
  });
  if (!res.ok) { setMeta("映射保存失败：" + (res.message || "")); return; }
  state.parsed = res.parsed;
  state.wfData = { ...(state.wfData || {}), ok: true, parsed: res.parsed,
                   candidates: state.wfData.candidates, mapping: res.mapping,
                   source: state.wfData.source };
  renderWorkflowDetail(state.wfData);
  renderModel(state.wfData);
  setMeta("映射已保存");
  await loadInjection();
}

async function deleteWorkflow() {
  if (!state.workflow) return;
  if (!confirm(`删除工作流「${state.workflow}」？文件会移到 workflows\\_archive，ComfyUI 原目录不受影响。`)) return;
  const res = await postJSON("/api/workflows/delete", { name: state.workflow });
  setMeta(res.message || (res.ok ? "已删除" : "删除失败"));
  if (res.ok) await loadWorkflows();
}

async function importWorkflowFile(file) {
  if (!file) return;
  const text = await file.text();
  const res = await postJSON("/api/workflows/import", { name: file.name, content: text });
  if (!res.ok) { setMeta("导入失败：" + (res.message || "未知原因")); return; }
  setMeta(`已导入 ${res.entry.name}（${res.entry.format === "api" ? "API" : "UI"}，${res.entry.node_count} 节点）`);
  await loadWorkflows(res.entry.name);
}

function renderModel(data) {
  if (!data.ok) {
    $("#model").innerHTML = `<div class="bad">${esc(data.message || "解析失败")}</div>`;
    return;
  }
  const m = data.match || {};
  const meta = data.meta || {};
  const p = data.parsed || {};
  const sampler = p.sampler || {};
  const latent = p.latent || {};
  const loraChecks = meta.lora_checks || [];

  let html = "";
  if (m.ok) {
    html += `<div class="rowline"><span class="k">Checkpoint</span><span class="v">${esc(m.registered_name)}</span></div>`;
    html += `<div class="rowline"><span class="k">架构 / 派系</span><span class="v">${esc(m.arch || "—")} / ${esc(m.family || "—")}</span></div>`;
    html += `<div class="rowline"><span class="k">Profile</span><span class="v">${esc(m.profile_relpath)}</span></div>`;
  } else {
    html += `<div class="rowline"><span class="k">Checkpoint</span><span class="v">${esc((p.checkpoint || {}).name || "—")}</span></div>`;
    html += `<div style="margin-top:6px"><span class="pill bad">未登记</span>
      <span class="muted small">${esc(data.context_message || m.message || "")}</span></div>`;
  }
  loraChecks.forEach((l) => {
    const cls = l.state === "ok" ? "ok" : (l.state === "incompatible" ? "bad" : "warn");
    html += `<div class="rowline"><span class="v">${esc(l.name)}</span>
      <span class="pill ${cls}">${esc(l.lora_arch || "未知")}</span></div>`;
  });
  const bits = [];
  if (sampler.sampler_name) bits.push(String(sampler.sampler_name));
  if (sampler.scheduler) bits.push(String(sampler.scheduler));
  if (sampler.steps != null) bits.push(`${sampler.steps} 步`);
  if (sampler.cfg != null) bits.push(`CFG ${sampler.cfg}`);
  if (latent.width) bits.push(`${latent.width}×${latent.height}`);
  if (bits.length) {
    html += `<div class="rowline"><span class="k">工作流参数</span><span class="v">${esc(bits.join(" · "))}</span></div>`;
  }
  const posNodes = ((p.positive || {}).node_ids || []).join("、") || "未判定";
  const negNodes = ((p.negative || {}).node_ids || []).join("、") || "未判定";
  html += `<div class="rowline"><span class="k">正 / 负节点</span><span class="v">${esc(posNodes)} / ${esc(negNodes)}</span></div>`;
  if (meta.warnings && meta.warnings.length) {
    html += `<div class="small" style="color:var(--warn);margin-top:6px">⚠ ${esc(meta.warnings.join("；"))}</div>`;
  }
  $("#model").className = "mini";
  $("#model").innerHTML = html;
}

async function loadInjection() {
  const pre = $("#inject");
  if (!state.workflow) { pre.textContent = "（未选择工作流）"; return; }
  const data = await getJSON("/api/context?workflow=" + encodeURIComponent(state.workflow));
  if (!data.ok) {
    pre.textContent = "注入失败：" + (data.message || "未知原因");
    $("#injmeta").textContent = "";
    return;
  }
  const meta = data.meta || {};
  $("#injmeta").textContent =
    `system ${meta.system_prompt_file} ${meta.system_chars} 字 · profile ${meta.profile_file} ${meta.profile_chars} 字 · 合计 ${meta.injected_chars} 字符`;
  pre.textContent = data.system;
}

// ---------------------------------------------------------------- 会话
function shortDate(iso) {
  if (!iso) return "";
  return iso.slice(5, 16).replace("T", " ");
}

async function loadConversations(selectId) {
  const data = await getJSON("/api/conversations");
  renderConvList(data.conversations || []);
  if (!data.conversations.length) {
    await createConversation();
    return;
  }
  const wanted = selectId || state.convId || data.conversations[0].conversation_id;
  const exists = data.conversations.some((c) => c.conversation_id === wanted);
  await selectConversation(exists ? wanted : data.conversations[0].conversation_id);
}

function renderConvList(list) {
  const box = $("#convlist");
  if (!list.length) { box.innerHTML = `<div class="small muted" style="padding:10px">还没有会话</div>`; return; }
  box.innerHTML = list.map((c) => `
    <div class="conv-item ${c.conversation_id === state.convId ? "active" : ""}" data-id="${esc(c.conversation_id)}">
      <div class="info" data-act="open">
        <span class="t">${esc(c.title || "未命名对话")}</span>
        <span class="d">${esc(shortDate(c.updated_at))} · ${c.message_count} 条${c.checkpoint ? " · " + esc(c.checkpoint) : ""}</span>
      </div>
      <button class="del" data-act="del" title="删除（会移到 _archive）">×</button>
    </div>`).join("");
}

async function createConversation() {
  const res = await postJSON("/api/conversations", { workflow: state.workflow });
  if (!res.ok) return;
  state.convId = res.conversation.conversation_id;
  await selectConversation(state.convId);
  await refreshConvList();
}

async function refreshConvList() {
  const data = await getJSON("/api/conversations");
  renderConvList(data.conversations || []);
}

async function selectConversation(id) {
  const data = await getJSON("/api/conversations/" + encodeURIComponent(id));
  if (!data.ok) return;
  state.convId = id;
  state.conv = data.conversation;
  $("#convtitle").value = state.conv.title || "";
  const info = $("#convinfo");
  info.textContent = `${state.conv.checkpoint || "—"} · ${state.conv.profile_name || "—"} · ${state.conv.messages.length} 条消息`;

  if (state.conv.workflow_id && state.conv.workflow_id !== state.workflow) {
    const opts = Array.from($("#wf").options).map((o) => o.value);
    if (opts.includes(state.conv.workflow_id)) {
      $("#wf").value = state.conv.workflow_id;
      await selectWorkflow(state.conv.workflow_id);
    }
  }
  renderMessages(state.conv.messages || []);
  renderConvListFromState();
  await loadGenerations();
}

function renderConvListFromState() {
  document.querySelectorAll(".conv-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === state.convId);
  });
}

async function deleteConversation(id) {
  if (!confirm("确定删除这段对话？文件会移到 history\\conversations\\_archive，可手动找回。")) return;
  const res = await postJSON(`/api/conversations/${encodeURIComponent(id)}/delete`, {});
  if (!res.ok) { setMeta("删除失败：" + res.message); return; }
  const data = await getJSON("/api/conversations");
  if (!data.conversations.length) { await createConversation(); }
  else { await loadConversations(data.conversations[0].conversation_id); }
}

async function renameConversation(title) {
  if (!state.convId || !title.trim()) return;
  const res = await postJSON(`/api/conversations/${encodeURIComponent(state.convId)}/rename`,
    { title: title.trim() });
  if (res.ok) {
    state.conv.title = res.conversation.title;
    setMeta("标题已保存");
    await refreshConvList();
  }
}

// ---------------------------------------------------------------- 提示词切分
const HEADS = [
  ["positive", ["【Positive Prompt】", "【Positive 提示词】"]],
  ["negative", ["【Negative Prompt】", "【Negative 提示词】"]],
  ["settings", ["【Generation Settings】", "【生成设置】"]],
  ["adapt", ["【模型适配说明】", "【Model Adaptability Explanation】"]],
  ["pending", ["【待确认项】", "【Pending Confirmation Items】"]],
  ["model", ["【当前模型】", "【Current Model】"]],
];

function findHead(text, aliases, from) {
  let best = -1, hit = "";
  aliases.forEach((a) => {
    const i = text.indexOf(a, from);
    if (i >= 0 && (best < 0 || i < best)) { best = i; hit = a; }
  });
  return { idx: best, len: hit.length };
}

function extractParts(text) {
  const marks = [];
  HEADS.forEach(([key, aliases]) => {
    const h = findHead(text, aliases, 0);
    if (h.idx >= 0) marks.push({ idx: h.idx, end: h.idx + h.len, key });
  });
  marks.sort((a, b) => a.idx - b.idx);
  const out = {};
  marks.forEach((m, i) => {
    const stop = i + 1 < marks.length ? marks[i + 1].idx : text.length;
    let body = text.slice(m.end, stop).trim();
    body = body.replace(/^```[A-Za-z]*\s*/, "").replace(/```$/g, "").trim();
    out[m.key] = body.replace(/\n```text\n?/g, "").trim();
  });
  return out;
}

async function copyText(text) {
  if (!text) { setMeta("这一条里没有可复制的内容"); return; }
  try {
    await navigator.clipboard.writeText(text);
    setMeta("已复制（" + text.length + " 字符）");
  } catch (e) {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    setMeta("已复制（" + text.length + " 字符）");
  }
}

// ---------------------------------------------------------------- 消息渲染
function renderMessages(messages) {
  const log = $("#log");
  if (!messages.length) {
    log.innerHTML = `<div class="empty muted">这段会话还没有消息，从下面开始说画面构想。</div>`;
    return;
  }
  log.innerHTML = "";
  messages.forEach((m) => {
    const div = document.createElement("div");
    div.className = "msg " + (m.role === "user" ? "user" : "assistant");
    if (m.role === "user") {
      div.textContent = m.content;
      const when = document.createElement("span");
      when.className = "when";
      when.textContent = shortDate(m.at);
      div.appendChild(when);
    } else {
      div.textContent = m.content;
      if (m.meta && m.meta.guard_ok === false) {
        const warn = document.createElement("div");
        warn.className = "small";
        warn.style.color = "var(--warn)";
        warn.textContent = "⚠ 这条输出被标记为可能失控";
        div.appendChild(warn);
      }
      const bar = document.createElement("div");
      bar.className = "msg-actions";
      const parts = extractParts(m.content);
      if (parts.positive) {
        const gen = document.createElement("button");
        gen.className = "act primary";
        gen.textContent = "出图";
        gen.addEventListener("click", () => runGeneration({
          positive: parts.positive, negative: parts.negative || "" }));
        bar.appendChild(gen);
      }
      [["复制 Positive", parts.positive], ["复制 Negative", parts.negative], ["复制全文", m.content]]
        .forEach(([label, value]) => {
          const b = document.createElement("button");
          b.className = "act";
          b.textContent = label;
          b.addEventListener("click", () => copyText(value || ""));
          bar.appendChild(b);
        });
      div.appendChild(bar);
      const when = document.createElement("span");
      when.className = "when";
      when.textContent = shortDate(m.at) +
        (m.meta && m.meta.attempts > 1 ? " · 自动重试 " + m.meta.attempts + " 次" : "");
      div.appendChild(when);
    }
    log.appendChild(div);
  });
  log.scrollTop = log.scrollHeight;
}

function addMessage(role, text, extra) {
  const log = $("#log");
  if (log.querySelector(".empty")) log.innerHTML = "";
  const div = document.createElement("div");
  div.className = "msg " + role + (extra && extra.error ? " err" : "");
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

function setMeta(text) { $("#meta").textContent = text || ""; }

// ---------------------------------------------------------------- 发送
async function send() {
  if (state.busy) return;
  const box = $("#msg");
  const text = box.value.trim();
  if (!text) return;
  if (!state.convId) { await createConversation(); if (!state.convId) return; }
  if (!state.workflow) {
    addMessage("assistant", "请先选择一个工作流（工作流决定读取哪个 Checkpoint）。", { error: true });
    return;
  }

  state.busy = true;
  $("#send").disabled = true;
  box.value = "";
  if ($("#log").querySelector(".empty")) $("#log").innerHTML = "";
  addMessage("user", text);
  const pending = addMessage("assistant", "生成中…（模型加载可能要几十秒）");

  try {
    const res = await postJSON("/api/chat", {
      conversation_id: state.convId,
      message: text,
      workflow: state.workflow,
    });
    pending.remove();
    if (!res.ok) {
      addMessage("assistant", (res.message || "失败") + (res.hint ? "\n" + res.hint : ""), { error: true });
      showError(res.message || "对话失败", res.hint || "", { reason: res.reason });
      return;
    }
    state.conv = res.conversation;
    renderMessages(state.conv.messages);
    renderMeta(res);
    await refreshConvList();
    await loadRuntime();
  } catch (e) {
    pending.remove();
    addMessage("assistant", "请求异常：" + e, { error: true });
    showError("对话请求异常", String(e), {});
  } finally {
    state.busy = false;
    $("#send").disabled = false;
  }
}

async function regenerate() {
  if (state.busy || !state.convId) return;
  state.busy = true;
  $("#regenerate").disabled = true;
  const pending = addMessage("assistant", "重新生成中…");
  try {
    const res = await postJSON("/api/chat", {
      conversation_id: state.convId,
      regenerate: true,
      workflow: state.workflow,
    });
    pending.remove();
    if (!res.ok) {
      addMessage("assistant", res.message || "失败", { error: true });
      showError(res.message || "重新生成失败", res.hint || "", { reason: res.reason });
      return;
    }
    state.conv = res.conversation;
    renderMessages(state.conv.messages);
    renderMeta(res);
    await refreshConvList();
    await loadRuntime();
  } catch (e) {
    pending.remove();
    addMessage("assistant", "请求异常：" + e, { error: true });
    showError("重新生成请求异常", String(e), {});
  } finally {
    state.busy = false;
    $("#regenerate").disabled = false;
  }
}

function renderMeta(res) {
  const meta = res.meta || {};
  const usage = res.usage || {};
  const bits = [
    `注入 ${meta.injected_chars || "?"} 字符`,
    meta.profile_file ? `profile ${meta.profile_file}` : "",
    res.attempts > 1 ? `自动重试 ${res.attempts} 次` : "",
    usage.prompt_tokens ? `输入 ${usage.prompt_tokens} tok` : "",
    usage.output_tokens ? `输出 ${usage.output_tokens} tok` : "",
    res.auto_saved === false ? "未落盘（设置里关了自动保存）" : "已保存",
    res.prompt ? `提示词记录 ${res.prompt.prompt_id}` : "",
  ].filter(Boolean);
  setMeta(bits.join(" · "));
}

// ---------------------------------------------------------------- 出图（阶段 5）
function clipText(text, n) {
  const t = String(text || "").replace(/\s+/g, " ").trim();
  return t.length > n ? t.slice(0, n) + "…" : t;
}

function genParamsText(g) {
  const params = g.params || {};
  const s = params.sampler || {};
  const l = params.latent || {};
  const bits = [];
  if (s.seed != null) bits.push("seed " + s.seed);
  if (s.steps != null) bits.push(s.steps + " 步");
  if (s.cfg != null) bits.push("CFG " + s.cfg);
  if (s.sampler_name) bits.push(s.sampler_name);
  if (s.scheduler) bits.push(s.scheduler);
  if (l.width) bits.push(l.width + "×" + l.height);
  return bits.join(" · ");
}

function genVramText(g) {
  const v = g.vram;
  if (!v || !v.auto) return "";
  const names = {
    ollama_unload: "卸载 Ollama",
    comfy_free: "释放 ComfyUI",
    ollama_reload: "恢复 Ollama",
    context_restore: "恢复对话",
  };
  const parts = (v.steps || [])
    .filter((s) => names[s.name])
    .map((s) => `${names[s.name]}${s.ok ? "✓" : "✗"}`);
  const before = v.vram_before || {};
  const after = v.vram_after || {};
  if (before.ok && after.ok) {
    parts.push(`显存 ${before.used_mb}→${after.used_mb} MB`);
  }
  if (!v.ollama_reloaded && (v.ollama_loaded_before || []).length) {
    parts.push("Ollama 未恢复");
  }
  return parts.join(" · ");
}

function genCardHtml(g) {
  const status = g.status || "running";
  const pill = status === "done" ? "ok" : (status === "error" ? "bad" : "warn");
  const label = status === "done" ? "已完成" : (status === "error" ? "失败" : "出图中");
  const imgs = (g.images || []).filter((i) => i.url).map((i) => `
      <button type="button" class="gen-img" data-act="preview" data-gid="${esc(g.generation_id)}" data-index="${esc(i.index)}" data-url="${esc(i.url)}" title="放大预览">
        <img src="${esc(i.url)}" alt="${esc(g.generation_id)} 第 ${esc(i.index)} 张" loading="lazy">
      </button>`).join("");
  const dur = g.duration_sec ? ` · ${esc(g.duration_sec)} 秒` : "";
  const pid = g.prompt_id ? ` · prompt ${esc(String(g.prompt_id).slice(0, 8))}` : "";
  const errActions = g.error ? `<div class="error-actions">
      <button class="act" data-act="showlog">查看日志</button>
      <button class="act" data-act="copyerror" data-gid="${esc(g.generation_id)}">复制错误</button>
    </div>` : "";
  return `<div class="gen-card" data-gid="${esc(g.generation_id)}">
    <div class="gen-head">
      <span class="pill ${pill}">${label}</span>
      <span class="gid">${esc(g.generation_id)}</span>
      <span class="muted small">${esc(shortDate(g.created_at))}${dur}${pid}</span>
    </div>
    ${imgs ? `<div class="gen-imgs">${imgs}</div>` : ""}
    ${genParamsText(g) ? `<div class="gen-params small">${esc(genParamsText(g))}</div>` : ""}
    ${genVramText(g) ? `<div class="gen-params small vram-line">显存：${esc(genVramText(g))}</div>` : ""}
    ${g.error ? `<div class="small bad-text">${esc(g.error)}</div>` : ""}
    ${errActions}
    <div class="gen-prompt small muted">正向：${esc(clipText(g.positive, 150))}</div>
    <div class="gen-actions">
      <button class="act" data-act="retry" data-gid="${esc(g.generation_id)}" data-fresh="${status === "done" ? "1" : "0"}">${status === "done" ? "再画一张（新种子）" : "重试"}</button>
      <button class="act" data-act="copyparams" data-gid="${esc(g.generation_id)}">复制参数</button>
    </div>
  </div>`;
}

function renderGallery() {
  const box = $("#gallery");
  const list = state.generations || [];
  $("#gcount").textContent = list.length ? `（${list.length}）` : "";
  if (!list.length) {
    box.innerHTML = `<div class="small muted">还没有出图。展开一条提示词后点“出图”。</div>`;
    return;
  }
  box.innerHTML = list.map(genCardHtml).join("");
}

async function loadGenerations() {
  const cid = state.convId || "";
  const data = await getJSON("/api/generations?conversation_id=" + encodeURIComponent(cid) + "&limit=40");
  state.generations = data.generations || [];
  renderGallery();
}

function addPendingCard(text) {
  const box = $("#gallery");
  if (box.querySelector(".small.muted") && !state.generations.length) box.innerHTML = "";
  const div = document.createElement("div");
  div.className = "gen-card pending";
  div.innerHTML = `<div class="gen-head"><span class="pill warn">出图中…</span>
      <span class="muted small">已提交 ComfyUI，等 GPU 跑完（832×1216 · 35 步约 1 分钟）</span></div>
    <div class="small muted">${esc(clipText(text || "等待结果", 150))}</div>`;
  box.prepend(div);
  return div;
}

async function runGeneration(body) {
  if (state.genBusy) { setMeta("上一张还在出，等它结束"); return; }
  if (!state.workflow) { setMeta("先在工作流里选一个完整工作流（要含 KSampler 与 SaveImage）"); return; }
  if (!body || !body.positive) { setMeta("这条回复里没有可用正向提示词"); return; }
  state.genBusy = true;
  const pending = addPendingCard(body.positive);
  try {
    const payload = {
      conversation_id: state.convId || "",
      workflow: state.workflow,
      positive: body.positive || "",
      negative: body.negative || "",
    };
    if ($("#randseed").checked) payload.seed = "randomize";
    const res = await postJSON("/api/generate", payload);
    pending.remove();
    if (!res.ok) {
      const msg = (res.message || "出图失败") + (res.hint ? "；" + res.hint : "");
      setMeta(msg);
      showError(msg, "", { reason: res.reason, generation_id: res.generation_id });
    } else {
      const n = ((res.generation || {}).images || []).length;
      setMeta(`出图完成 ${res.generation_id} · ${res.duration_sec} 秒 · ${n} 张 · ${res.prompt_id}`);
      toast(`出图完成 ${res.generation_id} · ${res.duration_sec} 秒`, "ok");
    }
    await loadGenerations();
    await loadStatus();
    await loadRuntime();
  } catch (e) {
    pending.remove();
    setMeta("出图请求异常：" + e);
    showError("出图请求异常", String(e), {});
  } finally {
    state.genBusy = false;
  }
}

async function retryGeneration(gid, fresh) {
  if (state.genBusy) { setMeta("上一张还在出，等它结束"); return; }
  state.genBusy = true;
  const pending = addPendingCard(fresh ? "再画一张（新种子）" : "重试同一组参数");
  try {
    const res = await postJSON(`/api/generations/${encodeURIComponent(gid)}/retry`,
      fresh ? { randomize: true } : {});
    pending.remove();
    if (res.ok) {
      setMeta(`已重新出图 ${res.generation_id} · ${res.duration_sec} 秒`);
      toast(`已重新出图 ${res.generation_id}`, "ok");
    } else {
      const msg = (res.message || "重试失败") + (res.hint ? "；" + res.hint : "");
      setMeta(msg);
      showError(msg, "", { reason: res.reason, retry_of: gid });
    }
    await loadGenerations();
    await loadStatus();
    await loadRuntime();
  } catch (e) {
    pending.remove();
    setMeta("重试请求异常：" + e);
    showError("重试请求异常", String(e), {});
  } finally {
    state.genBusy = false;
  }
}

function copyGenParams(gid) {
  const g = (state.generations || []).find((x) => x.generation_id === gid);
  if (!g) return;
  const params = g.params || {};
  const s = params.sampler || {};
  const l = params.latent || {};
  const text = [
    `generation_id=${g.generation_id}`,
    `prompt_id=${g.prompt_id || ""}`,
    `checkpoint=${g.checkpoint || ""}`,
    `seed=${s.seed}`, `steps=${s.steps}`, `cfg=${s.cfg}`,
    `sampler=${s.sampler_name}`, `scheduler=${s.scheduler}`,
    `size=${l.width}x${l.height}`, `batch=${l.batch}`,
    `positive=${g.positive || ""}`, `negative=${g.negative || ""}`,
  ].join("\n");
  copyText(text);
}

// ---------------------------------------------------------------- 图片预览
function imageOf(gid, index) {
  const gen = (state.generations || []).find((g) => g.generation_id === gid);
  if (!gen) return null;
  const img = (gen.images || []).find((i) => Number(i.index) === Number(index));
  return img ? { gen, img } : null;
}

function applyPreviewZoom() {
  const img = $("#previewImg");
  img.style.transform = "scale(" + state.previewZoom + ")";
  $("#zoomReset").textContent = state.previewZoom === 1 ? "适应" : Math.round(state.previewZoom * 100) + "%";
}

function openPreview(gid, index, url) {
  const found = imageOf(gid, index);
  const img = $("#previewImg");
  img.src = url;
  img.alt = gid + " 第 " + index + " 张";
  state.previewGid = gid;
  state.previewIndex = Number(index) || 1;
  state.previewZoom = 1;
  applyPreviewZoom();
  $("#previewCaption").textContent = "图片预览 · " + gid + " · 第 " + state.previewIndex + " 张";
  $("#previewDownload").href = url;
  $("#previewDownload").setAttribute("download",
    (found && found.img.filename) || (gid + "-" + state.previewIndex + ".png"));
  if (found) {
    const g = found.gen;
    const p = g.params || {};
    const s = p.sampler || {};
    const l = p.latent || {};
    const bits = [
      "文件 " + (found.img.filename || ""),
      found.img.bytes ? (found.img.bytes / 1024 / 1024).toFixed(2) + " MB" : "",
      s.seed != null ? "seed " + s.seed : "",
      s.steps != null ? s.steps + " 步" : "",
      s.cfg != null ? "CFG " + s.cfg : "",
      s.sampler_name || "", s.scheduler || "",
      l.width ? l.width + "×" + l.height : "",
      g.duration_sec ? g.duration_sec + " 秒" : "",
    ].filter(Boolean);
    $("#previewMeta").textContent = bits.join(" · ") + "　正向：" + clipText(g.positive, 220);
  } else {
    $("#previewMeta").textContent = "";
  }
  $("#previewModal").hidden = false;
  syncBodyLock();
}

function closePreview() {
  $("#previewModal").hidden = true;
  $("#previewImg").src = "";
  syncBodyLock();
}

// ---------------------------------------------------------------- 设置
function appSettings() {
  return (state.settings && state.settings.settings && state.settings.settings.application) || {};
}

function shouldConfirm() {
  const value = appSettings().confirm_delete;
  return value !== false;
}

function sysRows(target, rows) {
  const el = $(target);
  if (!el) return;
  el.innerHTML = rows.filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `<div class="sys-row"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`)
    .join("");
}

function renderSystem(sys) {
  if (!sys) return;
  const app = sys.app || {};
  const rtp = state.runtime || {};
  sysRows("#sysVersion", [
    ["版本", app.version],
    ["数据目录", app.base_dir],
    ["配置文件", app.config_path],
    ["已运行", rtp.uptime_sec != null ? fmtDuration(rtp.uptime_sec) : ""],
  ]);
  const ol = sys.ollama || {};
  const cf = sys.comfyui || {};
  sysRows("#sysServices", [
    ["Ollama", ol.base_url + " · 模型 " + (ol.model || "")],
    ["ComfyUI", cf.base_url],
    ["工作流目录", cf.workflows_dir],
    ["Checkpoint 目录", cf.models_dir],
    ["LoRA 目录", cf.loras_dir],
  ]);
  const paths = sys.paths || {};
  sysRows("#sysPaths", [
    ["对话 / 出图记录", paths.history],
    ["设置", paths.settings],
    ["出图原图", paths.outputs],
    ["工作台工作流", paths.workflows],
    ["备份", paths.backups],
    ["日志", paths.logs],
  ]);
  const v = sys.vram || {};
  sysRows("#sysVram", [
    ["自动管理", v.auto_manage ? "开" : "关"],
    ["出图前空闲阈值", (v.min_free_mb || 0) + " MB"],
    ["等显存释放", (v.wait_free_seconds || 0) + " 秒"],
    ["卸载 / 恢复等待", (v.unload_wait_seconds || 0) + " / " + (v.reload_wait_seconds || 0) + " 秒"],
    ["出图后 /free", v.free_comfy_after ? "开" : "关"],
    ["严格模式", v.strict_vram ? "开（空闲不够直接失败）" : "关（只警告）"],
    ["恢复 keep_alive", v.reload_keep_alive || ""],
  ]);
  const h = sys.history || {};
  const bk = sys.backups || {};
  const lg = sys.logs || {};
  sysRows("#sysBackupInfo", [
    ["对话 / 归档", (h.conversations || 0) + " / " + (h.archived || 0)],
    ["提示词 / 出图", (h.prompts || 0) + " / " + (h.generations || 0)],
    ["备份数量 / 占用", (bk.count || 0) + " 个 · " + ((bk.bytes || 0) / 1024 / 1024).toFixed(2) + " MB"],
    ["设置备份", sys.settings && sys.settings.backup_exists ? "有" : "暂无"],
  ]);
  const integ = sys.integrity || {};
  const issues = [];
  [["missing_profiles", "缺 profile"], ["orphan_profiles", "孤立 profile"],
   ["index_without_db", "索引多出"], ["db_without_index", "索引缺项"],
   ["missing_checkpoints", "磁盘缺 checkpoint"]].forEach(([key, label]) => {
    const list = integ[key] || [];
    if (list.length) issues.push(label + "：" + list.join("、"));
  });
  if ((integ.parse_problems || []).length) issues.push("解析问题：" + integ.parse_problems.join("；"));
  $("#sysIntegrity").innerHTML =
    `<span class="${integ.ok ? "ok" : "bad"}">${integ.ok ? "规则包体检通过" : "规则包体检有问题"}</span>` +
    ` · 数据库 ${esc(integ.db_entries)} 条 / profile 文件 ${esc(integ.profile_files)} / 索引 ${esc(integ.index_entries)}` +
    (issues.length ? `<br><span class="bad">${esc(issues.join("；"))}</span>` : "");
  const files = (lg.files || []).map((f) => `${f.name} ${(f.bytes / 1024).toFixed(0)} KB`).join(" · ");
  $("#sysLogs").innerHTML = `日志文件：${esc(files || "暂无")}<br>路径：<span class="muted">${esc(lg.path || "")}</span>`;
}

async function loadSettings() {
  const data = await getJSON("/api/settings");
  if (!data.ok) { showError("读取设置失败", data.message || ""); return; }
  state.settings = data;
  const app = data.settings.application || {};
  const chat = data.settings.chat || {};
  $("#setAutoSave").checked = app.auto_save_history !== false;
  $("#setAutoRestore").checked = app.auto_restore_ollama !== false;
  $("#setConfirmDelete").checked = app.confirm_delete !== false;
  $("#setHistory").value = chat.history_max_messages || 20;
  $("#setVariant").value = chat.system_prompt_variant || "精简版";
  renderSystem(data.system || {});
  $("#settingsFeedback").textContent = "读取于 " + new Date().toLocaleTimeString();
  await loadBackups();
}

async function saveSettings() {
  const body = {
    application: {
      auto_save_history: $("#setAutoSave").checked,
      auto_restore_ollama: $("#setAutoRestore").checked,
      confirm_delete: $("#setConfirmDelete").checked,
      theme: "dark",
    },
    chat: {
      history_max_messages: Number($("#setHistory").value || 20),
      system_prompt_variant: $("#setVariant").value,
    },
  };
  const res = await postJSON("/api/settings", body);
  if (!res.ok) { showError("保存设置失败", res.message || ""); return; }
  state.settings = { ...(state.settings || {}), settings: res.settings, info: res.info };
  const warnings = res.warnings || [];
  $("#settingsFeedback").textContent = warnings.length ? warnings.join("；") : "已保存（旧配置已备份）";
  toast(warnings.length ? "设置已保存，部分值被收窄：" + warnings.join("；")
                        : "设置已保存", warnings.length ? "warn" : "ok");
  await loadSettings();
  await loadRuntime();
}

async function openSettings() {
  $("#settingsModal").hidden = false;
  syncBodyLock();
  await loadSettings();
  await loadRuntime();
}

function closeSettings() {
  $("#settingsModal").hidden = true;
  syncBodyLock();
}

// ---------------------------------------------------------------- 备份
function fmtBytes(n) {
  n = Number(n || 0);
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / 1024 / 1024).toFixed(2) + " MB";
}

function renderBackups(data) {
  state.backups = data.backups || [];
  const info = data.info || {};
  $("#backupInfo").textContent = `${info.count || 0} 个备份 · ${fmtBytes(info.bytes)} · ${info.dir || ""}`;
  const box = $("#backupList");
  if (!state.backups.length) {
    box.innerHTML = `<div class="small muted">还没有备份。先点“立即备份”，再改程序或数据。</div>`;
    return;
  }
  box.innerHTML = state.backups.map((b) => {
    const counts = b.counts || {};
    const meta = [b.created_at, fmtBytes(b.bytes),
      `history ${counts.history || 0} · settings ${counts.settings || 0} · workflows ${counts.workflows || 0}`,
      b.note ? "备注：" + b.note : ""].filter(Boolean).join(" · ");
    return `<div class="backup-item ${b.ok ? "" : "bad"}">
      <div class="bi-main">
        <div class="bi-name">${esc(b.name)}</div>
        <div class="bi-meta">${esc(meta)}${b.ok ? "" : " · " + esc(b.error || "损坏")}</div>
      </div>
      <div class="bi-actions">
        <a class="act" href="/api/backups/${encodeURIComponent(b.name)}/download">下载</a>
        <button class="act" data-act="backupdel" data-name="${esc(b.name)}">删除</button>
      </div>
    </div>`;
  }).join("");
}

async function loadBackups() {
  try {
    const data = await getJSON("/api/backups");
    if (!data.ok) { showError("读取备份列表失败", data.message || ""); return; }
    renderBackups(data);
  } catch (e) {
    showError("读取备份列表异常", String(e), {});
  }
}

async function createBackup() {
  $("#backupCreate").disabled = true;
  try {
    const res = await postJSON("/api/backups", { note: $("#backupNote").value.trim() });
    if (!res.ok) { showError("创建备份失败", res.message || ""); return; }
    $("#backupNote").value = "";
    toast(`已创建备份 ${res.backup.name} · ${res.backup.file_count} 个文件 · ${fmtBytes(res.backup.bytes)}`, "ok");
    await loadBackups();
  } catch (e) {
    showError("创建备份异常", String(e), {});
  } finally {
    $("#backupCreate").disabled = false;
  }
}

async function deleteBackup(name) {
  if (shouldConfirm() && !confirm(`删除备份「${name}」？只会移到 backups\\_trash，可手动找回。`)) return;
  const res = await postJSON(`/api/backups/${encodeURIComponent(name)}/delete`, {});
  if (!res.ok) { showError("删除备份失败", res.message || ""); return; }
  toast("备份已移到回收目录", "warn");
  await loadBackups();
}

// ---------------------------------------------------------------- 日志面板
function renderLogs(data) {
  const entries = data.entries || [];
  const files = data.files || {};
  $("#logsPath").textContent = files.path || "logs\\workbench.log";
  $("#logsCount").textContent = `${entries.length} 条`;
  const box = $("#logsList");
  if (!entries.length) {
    box.innerHTML = `<div class="small muted">这个级别下没有日志。</div>`;
    return;
  }
  box.innerHTML = entries.map((e) => {
    const fields = e.fields ? JSON.stringify(e.fields) : "";
    return `<div class="log-entry ${esc(e.level)}">
      <div class="lg-head">
        <span class="lg-time">${esc(e.ts)}</span>
        <span class="lv ${esc(e.level)}">${esc(e.level)}</span>
        <span class="lg-scope">${esc(e.scope)}</span>
      </div>
      <div class="lg-msg">${esc(e.message)}</div>
      ${fields ? `<div class="lg-fields">${esc(fields)}</div>` : ""}
    </div>`;
  }).join("");
}

async function loadLogs() {
  const level = $("#logsLevel") ? $("#logsLevel").value : "";
  try {
    const data = await getJSON("/api/logs?limit=200" + (level ? "&level=" + encodeURIComponent(level) : ""));
    if (!data.ok) { showError("读取日志失败", data.message || ""); return; }
    renderLogs(data);
  } catch (e) {
    $("#logsList").innerHTML = `<div class="small bad-text">读取日志失败：${esc(e)}</div>`;
  }
}

function openLogs() {
  $("#logsModal").hidden = false;
  syncBodyLock();
  loadLogs();
}

function closeLogs() {
  $("#logsModal").hidden = true;
  syncBodyLock();
}

function syncBodyLock() {
  const anyOpen = ["#previewModal", "#settingsModal", "#logsModal"]
    .some((sel) => $(sel) && !$(sel).hidden);
  document.body.style.overflow = anyOpen ? "hidden" : "";
}


// ---------------------------------------------------------------- 绑定
function bind() {
  $("#wf").addEventListener("change", (e) => selectWorkflow(e.target.value));
  $("#wfimport").addEventListener("click", () => $("#wfFile").click());
  $("#wfFile").addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = "";
    await importWorkflowFile(file);
  });
  $("#send").addEventListener("click", send);
  $("#regenerate").addEventListener("click", regenerate);
  $("#msg").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); }
  });
  $("#newchat").addEventListener("click", createConversation);
  $("#newconv").addEventListener("click", createConversation);
  $("#exportconv").addEventListener("click", () => {
    if (!state.convId) return;
    window.location.href = "/api/conversations/" + encodeURIComponent(state.convId) + "/export";
  });
  $("#convlist").addEventListener("click", (e) => {
    const item = e.target.closest(".conv-item");
    if (!item) return;
    const id = item.dataset.id;
    if (e.target.dataset.act === "del") { deleteConversation(id); return; }
    selectConversation(id);
  });
  const title = $("#convtitle");
  title.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); renameConversation(title.value); title.blur(); }
  });
  title.addEventListener("blur", () => {
    if (state.conv && title.value.trim() !== (state.conv.title || "")) renameConversation(title.value);
  });
  $("#unload").addEventListener("click", async () => {
    const res = await postJSON("/api/unload", {});
    setMeta(res.message || (res.ok ? "已卸载" : "卸载失败"));
    loadStatus();
  });
  const rand = $("#randseed");
  rand.checked = localStorage.getItem("wb_randseed") === "1";
  rand.addEventListener("change", () => {
    localStorage.setItem("wb_randseed", rand.checked ? "1" : "0");
  });
  $("#gallery").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-act]");
    if (!btn) return;
    if (btn.dataset.act === "retry") retryGeneration(btn.dataset.gid, btn.dataset.fresh === "1");
    if (btn.dataset.act === "copyparams") copyGenParams(btn.dataset.gid);
    if (btn.dataset.act === "preview") openPreview(btn.dataset.gid, btn.dataset.index, btn.dataset.url);
    if (btn.dataset.act === "showlog") openLogs();
    if (btn.dataset.act === "copyerror") {
      const g = (state.generations || []).find((x) => x.generation_id === btn.dataset.gid);
      copyText((g && g.error) || "没有错误文本");
    }
  });

  // 运行状态 / 日志 / 设置
  $("#btnRuntime").addEventListener("click", async () => {
    await loadRuntime();
    await loadStatus();
    toast("运行状态已刷新", "ok", "", null, 1800);
  });
  $("#rtRefresh").addEventListener("click", async () => {
    await loadRuntime();
    await loadStatus();
  });
  $("#btnLogs").addEventListener("click", openLogs);
  $("#btnSettings").addEventListener("click", openSettings);
  $("#errorLog").addEventListener("click", openLogs);
  $("#errorClose").addEventListener("click", hideError);

  $("#settingsClose").addEventListener("click", closeSettings);
  $("#settingsReload").addEventListener("click", loadSettings);
  $("#settingsSave").addEventListener("click", saveSettings);
  $("#settingsTabs").addEventListener("click", (e) => {
    const tab = e.target.closest(".stab");
    if (!tab) return;
    document.querySelectorAll("#settingsTabs .stab").forEach((b) => b.classList.toggle("active", b === tab));
    document.querySelectorAll(".stab-panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === tab.dataset.tab));
  });
  $("#backupCreate").addEventListener("click", createBackup);
  $("#backupRefresh").addEventListener("click", loadBackups);
  $("#backupList").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-act=backupdel]");
    if (btn) deleteBackup(btn.dataset.name);
  });
  $("#logsClose").addEventListener("click", closeLogs);
  $("#logsRefresh").addEventListener("click", loadLogs);
  $("#logsLevel").addEventListener("change", loadLogs);

  // 图片预览
  $("#previewClose").addEventListener("click", closePreview);
  $("#zoomIn").addEventListener("click", () => {
    state.previewZoom = Math.min(4, state.previewZoom + 0.25); applyPreviewZoom();
  });
  $("#zoomOut").addEventListener("click", () => {
    state.previewZoom = Math.max(0.25, state.previewZoom - 0.25); applyPreviewZoom();
  });
  $("#zoomReset").addEventListener("click", () => {
    state.previewZoom = 1; applyPreviewZoom();
  });
  $("#previewImg").addEventListener("click", closePreview);
  $("#previewModal").addEventListener("click", (e) => {
    if (e.target === $("#previewModal")) closePreview();
  });

  // 点遮罩关闭（设置 / 日志）
  ["#settingsModal", "#logsModal"].forEach((sel) => {
    $(sel).addEventListener("click", (e) => {
      if (e.target === $(sel)) {
        if (sel === "#settingsModal") closeSettings(); else closeLogs();
      }
    });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("#previewModal").hidden) { closePreview(); return; }
    if (!$("#logsModal").hidden) { closeLogs(); return; }
    if (!$("#settingsModal").hidden) closeSettings();
  });
}

(async function boot() {
  bind();
  window.addEventListener("unhandledrejection", (e) => {
    showError("页面请求异常", String(e.reason || e), {});
  });
  await loadStatus();
  await loadRuntime();
  await loadWorkflows();
  await loadConversations();
  setInterval(() => {
    if (document.visibilityState === "visible") loadRuntime();
  }, 3000);
  setInterval(() => {
    if (document.visibilityState === "visible") loadStatus();
  }, 18000);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") { loadRuntime(); loadStatus(); }
  });
})();
