"use strict";

/* =========================================================
   Markdown Review — frontend
   Ported from doc-reviewer/project/* (React+Babel) to vanilla JS
   so no extra runtime is needed. Same DOM/selectors as the design,
   wired to the existing server API.
   ========================================================= */

const MAX_LEN = 2000;

// ---------- State ----------
const STATE = {
  // From /api/document
  blocks: [],
  comments: [],
  loadedMtime: 0,
  sidecarWarnings: [],
  changedBlockIds: new Set(),  // anchorKey strings from changed_block_ids

  // From /api/health (one-shot at boot)
  filePath: "",
  sidecarPath: "",
  serverHost: "",

  // UI
  composerFor: null,        // anchorKey
  activeId: null,           // anchorKey, transient highlight (auto-clears)
  editingCommentId: null,
  editingDraft: "",
  banner: null,             // {kind, text, action?}
  saveFailures: [],         // [{commentId|null, message}]
  pendingWrites: 0,
  sourceChanged: false,
  saving: false,            // brief in-flight indicator
  showSubmitModal: false,
  confirm: null,            // {title, body, danger, onConfirm}
  serverStopped: false,
  autoApply: false,         // submit-modal checkbox: auto-apply on Done
  doneAutoApply: false,     // sticky copy of autoApply at the moment Done succeeds
};

// Persistent DOM
let rootEl = null;
let blockNodes = new Map();      // anchorKey -> .block element
let composerEl = null;           // .floating-composer-wrap (mounted in .doc when active)
let composerCleanup = null;      // disposes resize listeners for the active composer
let docInnerEl = null;           // the .doc element where blocks + composer live
let activeTimer = null;
let toastTimer = null;
let toastEl = null;

// ---------- API ----------
async function api(method, path, body) {
  let resp;
  try {
    resp = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    return { ok: false, status: 0, payload: null, networkError: err };
  }
  let payload = null;
  try {
    const text = await resp.text();
    payload = text ? JSON.parse(text) : null;
  } catch (_) { /* non-JSON */ }
  return { ok: resp.ok, status: resp.status, payload };
}

// ---------- Anchor / block helpers ----------
function anchorKey(a) {
  return `${a.heading_path}::${a.block_index_in_section}::${a.text_hash}`;
}
function commentsForBlock(block) {
  const k = anchorKey(block.anchor);
  return STATE.comments.filter(c => anchorKey(c.anchor) === k);
}
function blockTypeLabel(b) {
  const k = b.kind || "block";
  if (k === "heading") return `h${b.heading_level || 1}`;
  if (k === "code_block") return "code";
  if (k === "blockquote") return "quote";
  return k;
}
function prettyCrumb(headingPath) {
  if (!headingPath) return "—";
  // "# Title > ## Sub > ### Detail" → "Title › Sub › Detail"
  return headingPath
    .split(">")
    .map(s => s.trim().replace(/^#+\s*/, ""))
    .filter(Boolean)
    .join(" › ") || "—";
}
function blockPreview(b) {
  const t = (b.plain_text || b.anchor.preview || "").trim();
  return t.length > 240 ? t.slice(0, 240) + "…" : t;
}
function relTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 0) return "just now";
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return d.toLocaleDateString();
}
function basenameOf(p) {
  if (!p) return "(unknown)";
  const i = p.lastIndexOf("/");
  return i === -1 ? p : p.slice(i + 1);
}
function dirsOf(p) {
  if (!p) return "";
  const i = p.lastIndexOf("/");
  if (i === -1) return "";
  const segs = p.slice(0, i).split("/").filter(Boolean);
  // show the last 3 dirs to keep the breadcrumb tight
  const tail = segs.slice(-3);
  return tail.length ? tail.join(" / ") + " / " : "";
}

// ---------- DOM helpers ----------
function el(tag, attrs, ...children) {
  const n = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "className") n.className = v;
      else if (k === "html") n.innerHTML = v;
      else if (k === "text") n.textContent = v;
      else if (k === "style" && typeof v === "object") Object.assign(n.style, v);
      else if (k === "dataset") Object.assign(n.dataset, v);
      else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2).toLowerCase(), v);
      else if (v === true) n.setAttribute(k, "");
      else n.setAttribute(k, v);
    }
  }
  for (const c of children) {
    if (c == null || c === false) continue;
    if (Array.isArray(c)) c.forEach(x => x != null && x !== false && n.appendChild(x.nodeType ? x : document.createTextNode(String(x))));
    else if (c.nodeType) n.appendChild(c);
    else n.appendChild(document.createTextNode(String(c)));
  }
  return n;
}

// ---------- Icon SVG ----------
const ICON = {
  comment: (size = 14) => svgIcon(size, '<path d="M2.5 3h11a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H6.5l-3 2.5V12H2.5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"/>'),
  plus:    (size = 14) => svgIcon(size, '<path d="M8 3v10M3 8h10"/>', "1.6"),
  x:       (size = 12) => svgIcon(size, '<path d="M4 4l8 8M12 4l-8 8"/>', "1.6"),
  warn:    (size = 14) => svgIcon(size, '<path d="M8 2l6.5 11.5h-13L8 2Z"/><path d="M8 7v3"/><circle cx="8" cy="12" r=".6" fill="currentColor"/>'),
  reload:  (size = 12) => svgIcon(size, '<path d="M3 8a5 5 0 0 1 8.5-3.5L13 6"/><path d="M13 3v3h-3"/><path d="M13 8a5 5 0 0 1-8.5 3.5L3 10"/><path d="M3 13v-3h3"/>'),
  check:   (size = 12) => svgIcon(size, '<path d="M3 8.5L6.5 12 13 4.5"/>', "2"),
  edit:    (size = 12) => svgIcon(size, '<path d="M11.5 2.5l2 2L5 13H3v-2l8.5-8.5Z"/>', "1.5"),
};
function svgIcon(size, paths, w = "1.5") {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", w);
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.innerHTML = paths;
  return svg;
}

// ---------- Initial load ----------
async function loadHealth() {
  const { ok, payload } = await api("GET", "/api/health");
  if (ok && payload) {
    STATE.filePath = payload.target_file || "";
    STATE.sidecarPath = STATE.filePath ? STATE.filePath + ".comments.json" : "";
  }
  STATE.serverHost = window.location.host;
}
async function loadDocument() {
  const { ok, payload } = await api("GET", "/api/document");
  if (!ok || !payload) {
    STATE.banner = { kind: "error", text: "Failed to load document." };
    renderApp();
    return;
  }
  STATE.blocks = payload.blocks || [];
  STATE.comments = payload.comments || [];
  STATE.loadedMtime = payload.source_mtime || 0;
  STATE.sidecarWarnings = payload.sidecar_warnings || [];
  STATE.changedBlockIds = new Set(payload.changed_block_ids || []);
  if (STATE.sidecarWarnings.length && !STATE.banner) {
    STATE.banner = { kind: "warn", text: "Sidecar warnings: " + STATE.sidecarWarnings.join("; ") };
  }
  renderApp();
}

// ---------- Top-level render ----------
function renderApp() {
  // Capture scrollTop from the about-to-be-discarded scroll containers so the
  // user doesn't get yanked to the top each time we re-render.
  const prevDocPane = rootEl ? rootEl.querySelector(".doc-pane") : null;
  const prevPanelList = rootEl ? rootEl.querySelector(".panel-list") : null;
  const savedDocScroll = prevDocPane ? prevDocPane.scrollTop : 0;
  const savedPanelScroll = prevPanelList ? prevPanelList.scrollTop : 0;

  // Clean up modals from prior render (toast manages itself).
  document.querySelectorAll(".modal-veil, .confirm").forEach(n => n.remove());
  // Drop the previous composer's resize listeners — its DOM goes away with the doc re-render below.
  if (composerCleanup) { composerCleanup(); composerCleanup = null; }
  composerEl = null;

  if (STATE.serverStopped) {
    rootEl.replaceChildren(renderStopped());
    return;
  }
  blockNodes = new Map();
  const app = el("div", { className: "app" },
    renderTopbar(),
    el("div", { className: "panes" },
      renderDocPane(),
      renderPanel(),
    ),
  );
  rootEl.replaceChildren(app);

  // Restore scroll positions on the freshly-mounted containers.
  const newDocPane = rootEl.querySelector(".doc-pane");
  const newPanelList = rootEl.querySelector(".panel-list");
  if (newDocPane) newDocPane.scrollTop = savedDocScroll;
  if (newPanelList) newPanelList.scrollTop = savedPanelScroll;

  // Toast + modals are appended outside the app grid
  if (STATE.showSubmitModal) document.body.appendChild(renderSubmitModal());
  if (STATE.confirm)         document.body.appendChild(renderConfirm());

  // Adjust doc-wrap alignment so the floating composer has room (must run
  // before mountComposer so its offsetTop math sees the final layout).
  applyDocLayout();

  // Mount composer if needed (must come AFTER blocks are in the DOM)
  if (STATE.composerFor) mountComposer(STATE.composerFor);
}

// Shift the doc-wrap left (and shrink its max-width if needed) so the floating
// composer at `left: calc(100% + 32px); width: 360px` doesn't get clipped by
// the doc-pane edge or hidden behind the comments panel.
function applyDocLayout() {
  const docPane = rootEl ? rootEl.querySelector(".doc-pane") : null;
  const docWrap = docPane ? docPane.querySelector(".doc-wrap") : null;
  if (!docPane || !docWrap) return;

  docWrap.classList.remove("shift-left");
  docWrap.style.maxWidth = "";

  if (!STATE.composerFor) return;
  // Below the stack-layout breakpoint the composer falls back to static flow.
  if (window.matchMedia("(max-width: 980px)").matches) return;

  const paneWidth = docPane.clientWidth;
  // Composer (width 360, left: calc(100% + 32px) relative to .doc which ends
  // 80px inside .doc-wrap) overhangs .doc-wrap.right by 360 + 32 - 80 = 312px.
  // Add 24px breathing room from the pane edge.
  const composerReserve = 312 + 24;
  const defaultMaxWidth = 720;

  // Centered layout: free space on the right = (paneWidth - maxWidth) / 2.
  if ((paneWidth - defaultMaxWidth) / 2 >= composerReserve) return;

  docWrap.classList.add("shift-left");
  const cappedMax = Math.max(360, paneWidth - composerReserve);
  if (cappedMax < defaultMaxWidth) {
    docWrap.style.maxWidth = cappedMax + "px";
  }
}

function renderStopped() {
  const auto = !!STATE.doneAutoApply;
  return el("div", { className: "stopped" },
    el("h1", null, "Server stopped"),
    auto
      ? el("p", null, "Claude is now applying your comments to the source markdown. Return to the terminal to watch the changes land.")
      : el("p", null, "You can close this tab. Returning to the terminal will show the next-turn prompt."),
  );
}

// ---------- Topbar ----------
function renderTopbar() {
  return el("div", { className: "topbar" },
    el("div", { className: "dot" }),
    el("div", { className: "path", title: STATE.filePath },
      el("span", { className: "seg", text: dirsOf(STATE.filePath) }),
      el("b", { text: basenameOf(STATE.filePath) }),
    ),
    el("div", { className: "url", text: STATE.serverHost ? `http://${STATE.serverHost}` : "" }),
  );
}

// ---------- Doc pane ----------
function renderDocPane() {
  const docInner = el("div", { className: "doc" });
  docInnerEl = docInner;

  for (const b of STATE.blocks) {
    const node = renderBlock(b);
    blockNodes.set(anchorKey(b.anchor), node);
    docInner.appendChild(node);
  }

  return el("div", { className: "doc-pane" },
    el("div", { className: "doc-wrap" }, docInner),
  );
}

function renderBlock(b) {
  const k = anchorKey(b.anchor);
  const cs = commentsForBlock(b);
  const hasComments = cs.length > 0;
  const isActive = STATE.activeId === k || STATE.composerFor === k;
  const isComposing = STATE.composerFor === k;
  const isRecentlyEdited = STATE.changedBlockIds.has(k);

  const cls =
    "block" +
    (hasComments ? " has-comments" : "") +
    (isActive ? " active-anchor" : "") +
    (isComposing ? " composing" : "") +
    (isRecentlyEdited ? " recently-edited" : "");

  const gutter = el("div", { className: "gutter" },
    el("button", {
      title: "Add comment",
      onclick: (e) => { e.stopPropagation(); openComposer(k); },
    }, hasComments ? ICON.plus() : ICON.comment()),
    hasComments ? el("div", {
      className: "count",
      title: cs.length + " comment" + (cs.length > 1 ? "s" : ""),
      onclick: (e) => { e.stopPropagation(); scrollToGroup(k); },
      text: String(cs.length),
    }) : null,
  );

  const content = el("div", { html: b.html });

  return el("div", {
    className: cls,
    dataset: { blockId: k },
  }, gutter, content);
}

// ---------- Panel ----------
function renderPanel() {
  return el("div", { className: "panel" },
    renderPanelHead(),
    renderPanelList(),
    renderPanelFoot(),
  );
}
function renderPanelHead() {
  return el("div", { className: "panel-head" },
    el("h2", null, "Comments", el("span", { className: "badge", text: String(STATE.comments.length) })),
    el("div", { className: "sub", title: STATE.sidecarPath, text: STATE.sidecarPath || "(no sidecar)" }),
  );
}
function renderPanelList() {
  const list = el("div", { className: "panel-list" });

  // Banners
  if (STATE.sourceChanged) {
    list.appendChild(renderBanner({
      kind: "warn",
      text: "Source file changed on disk. Anchors added after this point may be unstable.",
      action: { label: "Reload", onClick: reloadDoc, icon: ICON.reload },
    }));
  }
  if (STATE.saveFailures.length > 0) {
    list.appendChild(renderBanner({
      kind: "error",
      text: "Comment could not be saved — check disk space and permissions.",
      action: { label: "Acknowledge", onClick: () => { STATE.saveFailures = []; renderApp(); } },
    }));
  }
  if (STATE.banner) {
    list.appendChild(renderBanner(STATE.banner));
  }

  // Recently edited by Claude (blocks differing from the pre-apply snapshot).
  if (STATE.changedBlockIds.size > 0) {
    const editedRows = [];
    for (const b of STATE.blocks) {
      const k = anchorKey(b.anchor);
      if (!STATE.changedBlockIds.has(k)) continue;
      editedRows.push(
        el("div", {
          className: "edited-row",
          dataset: { groupId: k },
          onclick: () => scrollToBlock(k),
        },
          el("div", { className: "crumb", text: `${prettyCrumb(b.anchor.heading_path)} · ${blockTypeLabel(b)}` }),
          el("div", { className: "preview", text: blockPreview(b) }),
        ),
      );
    }
    if (editedRows.length > 0) {
      list.appendChild(
        el("div", { className: "recently-edited-section" },
          el("div", { className: "recently-edited-head" },
            ICON.edit(12),
            el("span", { text: `Recently edited by Claude (${editedRows.length})` }),
          ),
          el("div", { className: "recently-edited-body" }, ...editedRows),
        ),
      );
    }
  }

  // Orphans (comments whose anchor is not in current blocks)
  const blockKeys = new Set(STATE.blocks.map(b => anchorKey(b.anchor)));
  const grouped = new Map();
  for (const c of STATE.comments) {
    const k = anchorKey(c.anchor);
    if (!grouped.has(k)) grouped.set(k, []);
    grouped.get(k).push(c);
  }
  const orphanEntries = [...grouped.entries()].filter(([k]) => !blockKeys.has(k));
  if (orphanEntries.length > 0) {
    const orphanCount = orphanEntries.reduce((n, [, l]) => n + l.length, 0);
    list.appendChild(
      el("div", { className: "orphans" },
        el("div", { className: "orphans-head" },
          ICON.warn(12),
          el("span", { text: `Orphaned (${orphanCount})` }),
        ),
        el("div", { className: "orphans-body" },
          ...orphanEntries.map(([k, list]) =>
            el("div", { className: "orphan-row" },
              el("div", { className: "id", text: k }),
              ...list.map(c => renderComment(c, /*orphan*/ true)),
            )
          ),
        ),
      ),
    );
  }

  if (STATE.comments.length === 0) {
    list.appendChild(
      el("div", { className: "empty" },
        el("div", { className: "icon" }, ICON.comment(18)),
        el("div", { className: "t", text: "No comments yet" }),
        el("div", { className: "d", text: "Hover any block on the left and click the comment icon to add one." }),
      ),
    );
  } else {
    // Render groups in document order
    for (const b of STATE.blocks) {
      const k = anchorKey(b.anchor);
      const cs = grouped.get(k);
      if (!cs || cs.length === 0) continue;
      list.appendChild(renderGroup(b, cs));
    }
  }
  return list;
}

function renderGroup(block, comments) {
  const k = anchorKey(block.anchor);
  const isActive = STATE.activeId === k;
  return el("div", {
    className: "group" + (isActive ? " active" : ""),
    dataset: { groupId: k },
    onclick: () => scrollToBlock(k),
  },
    el("div", { className: "group-head" },
      el("div", { className: "crumb", text: `${prettyCrumb(block.anchor.heading_path)} · ${blockTypeLabel(block)}` }),
      el("div", { className: "preview", text: blockPreview(block) }),
    ),
    el("div", { className: "group-body" },
      ...comments
        .slice()
        .sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""))
        .map(c => renderComment(c, false)),
    ),
  );
}

function renderComment(c, isOrphan) {
  const isUnsaved = STATE.saveFailures.some(f => f.commentId === c.id);
  const isApplied = !!c.applied;
  const isEditing = STATE.editingCommentId === c.id;

  const meta = el("div", { className: "meta" },
    el("span", { className: "who", text: "You" }),
    el("span", { className: "dot" }),
    el("span", { text: relTime(c.updated_at || c.created_at) }),
    (c.updated_at && c.updated_at !== c.created_at)
      ? el("span", null, el("span", { className: "dot" }), document.createTextNode("edited"))
      : null,
  );

  const cls = "comment" + (isUnsaved ? " unsaved" : "") + (isApplied ? " applied" : "");

  if (isEditing) {
    const errEl = el("div", { className: "err", style: { color: "var(--danger)", fontSize: "12px", marginTop: "6px" } });
    let textarea;
    const counterEl = el("span", { className: "edit-counter", text: `${STATE.editingDraft.length} / ${MAX_LEN}` });
    const saveBtn = el("button", {
      className: "btn primary",
      onclick: async () => { await commitEdit(c, textarea, errEl); },
      disabled: STATE.editingDraft.trim().length === 0 || STATE.editingDraft.length > MAX_LEN,
    }, "Save");

    textarea = el("textarea", {
      className: "edit-area",
      value: STATE.editingDraft,
      oninput: (e) => {
        STATE.editingDraft = e.target.value;
        const len = STATE.editingDraft.length;
        counterEl.textContent = `${len} / ${MAX_LEN}`;
        counterEl.classList.toggle("over", len > MAX_LEN);
        saveBtn.disabled = STATE.editingDraft.trim().length === 0 || len > MAX_LEN;
        errEl.textContent = "";
      },
      onkeydown: (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
          e.preventDefault();
          commitEdit(c, textarea, errEl);
        } else if (e.key === "Escape") {
          e.preventDefault();
          cancelEdit();
        }
      },
    });
    textarea.value = STATE.editingDraft;

    const node = el("div", { className: cls },
      meta,
      textarea,
      errEl,
      el("div", { className: "edit-actions" },
        el("button", { className: "btn", onclick: cancelEdit }, "Cancel"),
        saveBtn,
        counterEl,
      ),
    );
    queueMicrotask(() => {
      try {
        textarea.focus({ preventScroll: true });
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
      } catch (_) {}
    });
    return node;
  }

  return el("div", { className: cls },
    meta,
    el("div", { className: "body", text: c.body || "" }),
    el("div", { className: "actions" },
      el("button", {
        className: "btn ghost",
        onclick: (e) => { e.stopPropagation(); startEdit(c); },
      }, "Edit"),
      renderDeleteAction(c),
    ),
  );
}

function renderDeleteAction(c) {
  // Two-step inline confirm; tracked via a closure-local element since it is short-lived UI.
  let confirming = false;
  let wrap;
  const renderInner = () => {
    wrap.replaceChildren(
      ...(confirming ? [
        el("button", {
          className: "btn ghost",
          onclick: (e) => { e.stopPropagation(); confirming = false; renderInner(); },
        }, "Cancel"),
        el("button", {
          className: "btn danger",
          onclick: (e) => { e.stopPropagation(); deleteComment(c.id); },
        }, "Delete"),
      ] : [
        el("button", {
          className: "btn ghost danger",
          onclick: (e) => { e.stopPropagation(); confirming = true; renderInner(); },
        }, "Delete"),
      ])
    );
  };
  wrap = el("span", { style: { display: "inline-flex", gap: "4px" } });
  renderInner();
  return wrap;
}

// ---------- Banner ----------
function renderBanner(b) {
  const node = el("div", { className: `banner ${b.kind}` },
    ICON.warn(),
    el("span", { className: "text", text: b.text }),
  );
  if (b.action) {
    const btn = el("button", { className: "action-btn", onclick: b.action.onClick }, b.action.label);
    node.appendChild(btn);
  }
  node.appendChild(
    el("span", {
      className: "x",
      title: "Dismiss",
      onclick: () => { if (b === STATE.banner) STATE.banner = null; node.remove(); },
    }, ICON.x()),
  );
  return node;
}

// ---------- Panel foot ----------
function renderPanelFoot() {
  const status = STATE.saving ? "Saving…" :
                 STATE.saveFailures.length ? "Save failed" :
                 `${STATE.comments.length} saved`;
  const time = new Date().toLocaleString(undefined, { hour: "2-digit", minute: "2-digit" });

  return el("div", { className: "panel-foot" },
    el("div", { className: "meta-line" },
      el("span", { text: status }),
      el("br"),
      el("span", { style: { opacity: 0.7 }, text: `v1 · ${time}` }),
    ),
    el("button", {
      className: "btn",
      disabled: STATE.comments.length === 0 || STATE.saving,
      onclick: askClearAll,
    }, "Clear"),
    el("button", {
      className: "btn primary submit",
      disabled: STATE.saving,
      onclick: () => { STATE.showSubmitModal = true; renderApp(); },
    }, "Submit & Done"),
  );
}

// ---------- Composer ----------
function openComposer(k) {
  STATE.composerFor = k;
  STATE.activeId = k;
  renderApp();
}
function closeComposer() {
  STATE.composerFor = null;
  STATE.activeId = null;
  renderApp();
}

function mountComposer(k) {
  if (!docInnerEl) return;
  const anchorEl = blockNodes.get(k);
  if (!anchorEl) return;

  const block = STATE.blocks.find(b => anchorKey(b.anchor) === k);
  if (!block) return;

  const wrap = el("div", { className: "floating-composer-wrap" });
  composerEl = wrap;
  const composer = renderComposerCard(block, k);
  wrap.appendChild(composer);

  // Position: anchor block's offsetTop within .doc (offsetParent)
  const updatePosition = () => {
    if (anchorEl.offsetParent !== docInnerEl && !docInnerEl.contains(anchorEl)) return;
    let top = 0;
    let n = anchorEl;
    // Walk offsetParent chain up to .doc
    while (n && n !== docInnerEl) {
      top += n.offsetTop;
      n = n.offsetParent;
    }
    wrap.style.top = top + "px";
  };
  updatePosition();
  const ro = new ResizeObserver(updatePosition);
  ro.observe(anchorEl);
  ro.observe(docInnerEl);
  window.addEventListener("resize", updatePosition);
  composerCleanup = () => { ro.disconnect(); window.removeEventListener("resize", updatePosition); };

  docInnerEl.appendChild(wrap);

  // Focus textarea (without scrolling)
  const ta = composer.querySelector("textarea");
  if (ta) {
    try { ta.focus({ preventScroll: true }); } catch (_) {}
    autoGrow(ta);
  }
}

function renderComposerCard(block, k) {
  let value = "";
  let saving = false;
  let textarea, footEl, counterEl, errEl, primaryBtn;

  const updateCounter = () => {
    const len = value.length;
    counterEl.textContent = `${len.toLocaleString()} / ${MAX_LEN.toLocaleString()}`;
    counterEl.className = "counter" + (len > MAX_LEN ? " over" : len > MAX_LEN - 200 ? " warn" : "");
    primaryBtn.disabled = saving || !value.trim() || value.length > MAX_LEN;
  };
  const setError = (msg) => {
    errEl.textContent = msg || "";
    errEl.style.display = msg ? "block" : "none";
  };

  const tryCancel = () => {
    if (value.trim().length > 0) {
      STATE.confirm = {
        title: "Discard draft?",
        body: "You'll lose what you've typed.",
        danger: true,
        confirmLabel: "Discard",
        onConfirm: () => { STATE.confirm = null; closeComposer(); },
      };
      renderApp();
    } else {
      closeComposer();
    }
  };

  const submit = async () => {
    if (!value.trim()) { setError("Comment can't be empty."); return; }
    if (value.length > MAX_LEN) { setError(`Too long — ${value.length}/${MAX_LEN} characters.`); return; }
    setError("");
    saving = true; primaryBtn.disabled = true; primaryBtn.textContent = "Saving…";
    STATE.saving = true;
    try {
      const { ok, status, payload } = await api("POST", "/api/comments", {
        anchor: block.anchor, body: value,
      });
      if (!ok) {
        if (status === 422) {
          const msg = (payload && payload.error) || "Invalid comment.";
          setError(`Validation error: ${msg}`);
        } else {
          STATE.saveFailures.push({ commentId: null, message: (payload && payload.error) || `HTTP ${status}` });
        }
        saving = false; primaryBtn.disabled = false; primaryBtn.textContent = "Add comment";
        STATE.saving = false;
        renderApp();
        return;
      }
      STATE.comments.push(payload.comment);
      STATE.pendingWrites = payload.pending_writes ?? STATE.pendingWrites;
      STATE.composerFor = null;
      STATE.activeId = null;
      STATE.saving = false;
      renderApp();
      showToast("Comment added");
    } catch (err) {
      STATE.saveFailures.push({ commentId: null, message: String(err) });
      STATE.saving = false;
      saving = false; primaryBtn.disabled = false; primaryBtn.textContent = "Add comment";
      renderApp();
    }
  };

  const head = el("div", { className: "head" },
    ICON.comment(12),
    el("span", { text: "New comment" }),
    el("span", { className: "crumb", text: `${prettyCrumb(block.anchor.heading_path)} › ${blockTypeLabel(block)}` }),
  );

  textarea = el("textarea", {
    placeholder: "What should change here?  (Cmd/Ctrl+Enter to submit, Esc to cancel)",
    oninput: (e) => { value = e.target.value; updateCounter(); if (errEl.textContent) setError(""); autoGrow(textarea); },
    onkeydown: (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); submit(); }
      else if (e.key === "Escape") { e.preventDefault(); tryCancel(); }
    },
  });

  errEl   = el("div", { className: "err", style: { display: "none" } });
  counterEl = el("span", { className: "counter", text: `0 / ${MAX_LEN.toLocaleString()}` });
  primaryBtn = el("button", {
    className: "btn primary",
    disabled: true,
    onclick: submit,
  }, "Add comment");

  footEl = el("div", { className: "foot" },
    el("span", { className: "hint", text: "Markdown supported · Cmd+Enter to submit" }),
    counterEl,
    el("button", { className: "btn ghost", onclick: tryCancel }, "Cancel"),
    primaryBtn,
  );

  return el("div", { className: "inline-composer" }, head, textarea, errEl, footEl);
}

function autoGrow(ta) {
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 320) + "px";
}

// ---------- Comment ops ----------
async function deleteComment(id) {
  STATE.saving = true;
  const { ok, status, payload } = await api("DELETE", `/api/comments/${encodeURIComponent(id)}`);
  STATE.saving = false;
  if (!ok) {
    if (status !== 409) {
      STATE.saveFailures.push({ commentId: id, message: (payload && payload.error) || "Delete failed" });
    }
    renderApp();
    return;
  }
  STATE.comments = STATE.comments.filter(c => c.id !== id);
  STATE.saveFailures = STATE.saveFailures.filter(f => f.commentId !== id);
  if (payload && payload.pending_writes != null) STATE.pendingWrites = payload.pending_writes;
  renderApp();
  showToast("Comment deleted");
}

function startEdit(c) {
  STATE.editingCommentId = c.id;
  STATE.editingDraft = c.body || "";
  renderApp();
}
function cancelEdit() {
  STATE.editingCommentId = null;
  STATE.editingDraft = "";
  renderApp();
}
async function commitEdit(c, textarea, errEl) {
  const body = textarea.value;
  if (!body.trim()) { errEl.textContent = "Comment can't be empty."; return; }
  if (body.length > MAX_LEN) { errEl.textContent = `Too long — ${body.length}/${MAX_LEN}.`; return; }
  STATE.saving = true;
  const { ok, status, payload } = await api("PUT", `/api/comments/${encodeURIComponent(c.id)}`, { body });
  STATE.saving = false;
  if (!ok) {
    if (status === 422) {
      errEl.textContent = "Validation error: " + ((payload && payload.error) || "");
    } else {
      STATE.saveFailures.push({ commentId: c.id, message: (payload && payload.error) || `HTTP ${status}` });
      cancelEdit();
    }
    renderApp();
    return;
  }
  const idx = STATE.comments.findIndex(x => x.id === c.id);
  if (idx >= 0) STATE.comments[idx] = payload.comment;
  if (payload.pending_writes != null) STATE.pendingWrites = payload.pending_writes;
  cancelEdit();
  showToast("Comment updated");
}

function askClearAll() {
  if (STATE.comments.length === 0) return;
  STATE.confirm = {
    title: "Clear all comments?",
    body: `This will remove ${STATE.comments.length} comment${STATE.comments.length === 1 ? "" : "s"} from the local sidecar.`,
    danger: true,
    confirmLabel: "Clear all",
    onConfirm: async () => {
      STATE.confirm = null;
      const ids = STATE.comments.map(c => c.id);
      STATE.saving = true; renderApp();
      for (const id of ids) {
        try { await api("DELETE", `/api/comments/${encodeURIComponent(id)}`); } catch (_) {}
      }
      // Refresh authoritative state from server
      await loadDocument();
      STATE.saving = false;
      renderApp();
      showToast("All comments cleared");
    },
  };
  renderApp();
}

// ---------- Submit modal & Done ----------
function buildSidecarPreview() {
  return {
    version: 1,
    file: STATE.filePath,
    updatedAt: new Date().toISOString(),
    comments: STATE.comments.map(c => ({
      anchor: c.anchor,
      crumb: prettyCrumb(c.anchor.heading_path),
      body: c.body,
      createdAt: c.created_at,
      updatedAt: c.updated_at,
    })),
  };
}
function renderSubmitModal() {
  const sidecar = buildSidecarPreview();
  const json = JSON.stringify(sidecar, null, 2);
  const fileLabel = STATE.filePath ? STATE.filePath.replace(/^.*?\/(?=[^/]+$)/, "") : "(file)";
  const nextPrompt = `Apply the comments in \`${STATE.sidecarPath}\` to \`${STATE.filePath}\`.`;

  let copyBtn, copyJsonBtn;
  const copy = (s, btn, original) => {
    if (navigator.clipboard) navigator.clipboard.writeText(s);
    btn.textContent = "Copied";
    setTimeout(() => { btn.textContent = original; }, 1400);
  };

  const close = () => { STATE.showSubmitModal = false; renderApp(); };

  copyBtn     = el("button", { className: "btn", onclick: () => copy(nextPrompt, copyBtn, "Copy prompt") }, "Copy prompt");
  copyJsonBtn = el("button", { className: "btn ghost", onclick: () => copy(json, copyJsonBtn, "Copy sidecar JSON") }, "Copy sidecar JSON");

  const autoApplyCheckbox = el("input", {
    type: "checkbox",
    id: "auto-apply-toggle",
    checked: STATE.autoApply,
    onchange: (e) => { STATE.autoApply = !!e.target.checked; },
  });
  const autoApplyRow = el("label", {
    className: "auto-apply-row",
    for: "auto-apply-toggle",
  },
    autoApplyCheckbox,
    el("span", { className: "auto-apply-text" },
      el("b", { text: "Auto-apply comments when I click Done" }),
      el("span", {
        className: "hint",
        text: "Claude will read the sidecar and edit the source markdown directly. Leave unchecked to just stop the server and apply later yourself.",
      }),
    ),
  );

  const veil = el("div", { className: "modal-veil", onclick: close },
    el("div", { className: "modal", onclick: (e) => e.stopPropagation() },
      el("div", { className: "h" },
        el("h3", null, "Submit & Done"),
        el("p", null,
          document.createTextNode(`${STATE.comments.length} comment${STATE.comments.length === 1 ? "" : "s"} saved at `),
          el("code", { text: STATE.sidecarPath || "(no sidecar)" }),
          document.createTextNode(". Paste this into your next Claude turn to apply them:"),
        ),
      ),
      el("div", { className: "body" },
        el("pre", { text: nextPrompt }),
        el("div", { className: "row" }, copyBtn, copyJsonBtn),
        el("pre", { style: { fontSize: "11.5px", maxHeight: "240px", overflow: "auto" }, text: json }),
        autoApplyRow,
      ),
      el("div", { className: "foot" },
        el("button", { className: "btn", onclick: close }, "Keep reviewing"),
        el("button", { className: "btn primary", onclick: clickDone, disabled: STATE.saving || STATE.saveFailures.length > 0 }, "Done — stop server"),
      ),
    ),
  );
  return veil;
}

async function clickDone() {
  STATE.saving = true;
  // Snapshot the choice now so renderStopped reflects what we sent even if
  // STATE.autoApply mutates later (shouldn't, but be defensive).
  const sentAutoApply = !!STATE.autoApply;
  // Update modal in place if visible
  renderApp();
  try {
    const { ok, payload } = await api("POST", "/api/done", { auto_apply: sentAutoApply });
    if (!ok) {
      const msg = (payload && payload.error) || "Server error";
      STATE.saveFailures.push({ commentId: null, message: msg });
      STATE.saving = false;
      renderApp();
      return;
    }
    STATE.doneAutoApply = !!(payload && payload.auto_apply);
    STATE.serverStopped = true;
    STATE.showSubmitModal = false;
    renderApp();
  } catch (_) {
    // Connection reset = expected when server shuts down. The browser never
    // sees the response, but our request did go through — trust the value
    // we sent.
    STATE.doneAutoApply = sentAutoApply;
    STATE.serverStopped = true;
    STATE.showSubmitModal = false;
    renderApp();
  }
}

// ---------- Confirm dialog ----------
function renderConfirm() {
  const c = STATE.confirm;
  const close = () => { STATE.confirm = null; renderApp(); };
  return el("div", { className: "confirm" },
    el("div", { className: "box" },
      el("h4", { text: c.title }),
      el("p", { text: c.body || "" }),
      el("div", { className: "row" },
        el("button", { className: "btn", onclick: close }, "Cancel"),
        el("button", {
          className: "btn " + (c.danger ? "danger" : "primary"),
          onclick: () => { close(); c.onConfirm && c.onConfirm(); },
        }, c.confirmLabel || "Confirm"),
      ),
    ),
  );
}

// ---------- Toast ----------
function showToast(text) {
  if (toastEl) toastEl.remove();
  toastEl = el("div", { className: "toast" },
    el("span", { className: "ok" }, ICON.check(14)),
    el("span", { text }),
  );
  document.body.appendChild(toastEl);
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { if (toastEl) { toastEl.remove(); toastEl = null; } }, 1800);
}

// ---------- Scroll helpers ----------
function scrollToBlock(k) {
  const el = blockNodes.get(k);
  if (!el) return;
  STATE.activeId = k;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  if (activeTimer) clearTimeout(activeTimer);
  // Update the active class without full re-render
  for (const [key, node] of blockNodes) {
    node.classList.toggle("active-anchor", key === k);
  }
  activeTimer = setTimeout(() => {
    if (STATE.activeId === k) {
      STATE.activeId = null;
      const node = blockNodes.get(k);
      if (node) node.classList.remove("active-anchor");
      // refresh group active state too
      const group = document.querySelector(`[data-group-id="${cssEscape(k)}"]`);
      if (group) group.classList.remove("active");
    }
  }, 1600);
  // Highlight matching panel group too
  for (const g of document.querySelectorAll("[data-group-id]")) {
    g.classList.toggle("active", g.dataset.groupId === k);
  }
}
function scrollToGroup(k) {
  const g = document.querySelector(`[data-group-id="${cssEscape(k)}"]`);
  if (!g) return;
  g.scrollIntoView({ behavior: "smooth", block: "center" });
  for (const x of document.querySelectorAll("[data-group-id]")) {
    x.classList.toggle("active", x.dataset.groupId === k);
  }
  if (activeTimer) clearTimeout(activeTimer);
  activeTimer = setTimeout(() => {
    const x = document.querySelector(`[data-group-id="${cssEscape(k)}"]`);
    if (x) x.classList.remove("active");
  }, 1600);
}
function cssEscape(s) {
  return (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/(["\\])/g, "\\$1");
}

// ---------- Reload ----------
async function reloadDoc() {
  STATE.sourceChanged = false;
  await loadDocument();
}

// ---------- mtime poll (lazy) ----------
async function checkMtime() {
  if (STATE.sourceChanged || STATE.serverStopped) return;
  const { ok, payload } = await api("GET", "/api/document/changed");
  if (ok && payload && payload.changed) {
    STATE.sourceChanged = true;
    renderApp();
  }
}

// ---------- Boot ----------
async function init() {
  rootEl = document.getElementById("root");
  await loadHealth();
  await loadDocument();
  // Lazy mtime poll: once on first interaction, then every 30s
  document.addEventListener("mousemove", checkMtime, { once: true });
  document.addEventListener("focusin", checkMtime, { once: true });
  setInterval(checkMtime, 30000);

  // Re-check doc/composer fit on viewport changes.
  window.addEventListener("resize", applyDocLayout);

  // Global keys
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (STATE.confirm) { STATE.confirm = null; renderApp(); return; }
      if (STATE.showSubmitModal) { STATE.showSubmitModal = false; renderApp(); return; }
      if (STATE.composerFor) { /* handled inside composer textarea */ }
    }
  });
}
document.addEventListener("DOMContentLoaded", init);
