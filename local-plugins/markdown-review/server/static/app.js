"use strict";

// ---- State (per Plan §3, verbatim shape) ----
const STATE = {
  blocks: [],          // Block[] from /api/document
  comments: [],        // Comment[]
  loadedMtime: 0,
  pendingWrites: 0,
  serverState: "ready",
  draftAnchor: null,   // Anchor object | null — which block has an open input
  draftBody: "",
  saveFailures: [],    // [{commentId, message}]
  sourceChanged: false // FR-08 banner state
};

// ---- DOM refs (resolved on DOMContentLoaded) ----
let docEl, commentsEl, bannersEl, doneBtn;
let blockTpl, inputTpl;

// ---- API helpers ----
async function api(method, path, body) {
  const resp = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let payload = null;
  try {
    const text = await resp.text();
    payload = text ? JSON.parse(text) : null;
  } catch (_) { /* non-JSON response */ }
  return { status: resp.status, ok: resp.ok, payload };
}

// ---- Anchor helpers ----
function anchorKey(a) {
  // Produce a stable string key from an anchor object.
  return `${a.heading_path}::${a.block_index_in_section}::${a.text_hash}`;
}

function commentsForAnchorKey(k) {
  return STATE.comments.filter(c => anchorKey(c.anchor) === k);
}

// ---- Initial load / reload ----
async function loadDocument() {
  const { ok, payload } = await api("GET", "/api/document");
  if (!ok) {
    showBanner("save-failure", "Failed to load document.");
    return;
  }
  STATE.blocks = payload.blocks;
  STATE.comments = payload.comments;
  STATE.loadedMtime = payload.source_mtime;
  if (payload.sidecar_warnings && payload.sidecar_warnings.length > 0) {
    showBanner("info", "Sidecar warnings: " + payload.sidecar_warnings.join("; "));
  }
  renderDoc();
  renderComments();
  updateDoneButton();
}

// ---- Render: doc pane ----
function renderDoc() {
  docEl.innerHTML = "";
  for (const block of STATE.blocks) {
    const k = anchorKey(block.anchor);
    const node = blockTpl.content.firstElementChild.cloneNode(true);
    node.dataset.anchor = k;
    node.querySelector(".block-content").innerHTML = block.html;
    if (commentsForAnchorKey(k).length > 0) {
      node.classList.add("has-comments");
    }
    node.querySelector(".comment-icon").addEventListener("click", () =>
      openCommentInput(block.anchor, node, null)
    );
    docEl.appendChild(node);
  }
}

// ---- Comment input UX (FR-13, FR-14, FR-15, FR-16, FR-17) ----
function openCommentInput(anchor, blockNode, existingComment) {
  // Close any existing open draft first (with discard-confirm if dirty).
  closeOpenInput().then(closed => {
    if (!closed) return;

    STATE.draftAnchor = anchor;
    STATE.draftBody = existingComment ? existingComment.body : "";

    blockNode.classList.add("has-open-input");

    const form = inputTpl.content.firstElementChild.cloneNode(true);
    form.dataset.anchor = anchorKey(anchor);
    if (existingComment) form.dataset.commentId = existingComment.id;

    const textarea = form.querySelector(".comment-body");
    const counter = form.querySelector(".char-counter");
    const submitBtn = form.querySelector(".comment-submit");
    const errorEl = form.querySelector(".comment-error");

    textarea.value = STATE.draftBody;
    updateCounter();

    function updateCounter() {
      const len = textarea.value.length;
      counter.textContent = `${len} / 2000`;
      counter.classList.toggle("over", len > 2000);
    }

    // FR-13: bare Enter inserts newline (textarea default); Cmd/Ctrl+Enter submits.
    // FR-15: live counter; enforce hard cap client-side.
    textarea.addEventListener("input", () => {
      // FR-15 hard cap — truncate to 2000 (server enforces too)
      if (textarea.value.length > 2000) {
        textarea.value = textarea.value.slice(0, 2000);
      }
      STATE.draftBody = textarea.value;
      updateCounter();
    });

    textarea.addEventListener("keydown", e => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        // FR-13: Cmd/Ctrl+Enter submits
        e.preventDefault();
        submitDraft(form, blockNode, anchor, existingComment);
      } else if (e.key === "Escape") {
        // FR-16: Escape — confirm if dirty, dismiss immediately if empty
        e.preventDefault();
        if (textarea.value.trim().length > 0) {
          confirmDiscard().then(confirmed => { if (confirmed) discardInput(blockNode); });
        } else {
          discardInput(blockNode);
        }
      }
    });

    // FR-13: submit button
    form.addEventListener("submit", e => {
      e.preventDefault();
      submitDraft(form, blockNode, anchor, existingComment);
    });

    blockNode.appendChild(form);
    textarea.focus();

    // FR-16: click-outside dismiss (with discard-confirm if dirty).
    // Defer listener so the click that opened the input doesn't immediately fire it.
    let outsideClickHandler;
    outsideClickHandler = ev => {
      if (form.contains(ev.target)) return;
      // Also ignore clicks on this block's own comment-icon (which re-opens the form).
      if (ev.target === blockNode.querySelector(".comment-icon")) return;
      document.removeEventListener("mousedown", outsideClickHandler, { capture: true });
      if (textarea.value.trim().length > 0) {
        ev.preventDefault();
        ev.stopPropagation();
        confirmDiscard().then(confirmed => { if (confirmed) discardInput(blockNode); });
      } else {
        discardInput(blockNode);
      }
    };
    setTimeout(() => {
      document.addEventListener("mousedown", outsideClickHandler, { capture: true });
    }, 0);
  });
}

function discardInput(blockNode) {
  const form = blockNode.querySelector(".comment-input");
  if (form) form.remove();
  blockNode.classList.remove("has-open-input");
  STATE.draftAnchor = null;
  STATE.draftBody = "";
}

async function closeOpenInput() {
  // Returns true if closing succeeded (no open draft, or user confirmed discard).
  const form = document.querySelector(".comment-input");
  if (!form) return true;
  const blockNode = form.closest(".block");
  const textarea = form.querySelector(".comment-body");
  if (textarea && textarea.value.trim().length > 0) {
    const confirmed = await confirmDiscard();
    if (!confirmed) return false;
  }
  if (blockNode) discardInput(blockNode);
  return true;
}

async function submitDraft(form, blockNode, anchor, existingComment) {
  const textarea = form.querySelector(".comment-body");
  const submitBtn = form.querySelector(".comment-submit");
  const errorEl = form.querySelector(".comment-error");
  const body = textarea.value;

  // FR-14: blank/whitespace-only rejection
  if (body.trim().length === 0) {
    errorEl.textContent = "Comment body cannot be blank.";
    errorEl.hidden = false;
    return;
  }

  // FR-15: oversize rejection (belt-and-suspenders; textarea input handler already truncates)
  if (body.length > 2000) {
    errorEl.textContent = `Body too long (${body.length} / 2000).`;
    errorEl.hidden = false;
    return;
  }

  errorEl.hidden = true;

  // FR-17: spinner if save takes >300ms
  let spinnerTimer = setTimeout(() => {
    if (!submitBtn.querySelector(".comment-submit-spinner")) {
      const sp = document.createElement("span");
      sp.className = "comment-submit-spinner";
      submitBtn.appendChild(sp);
    }
  }, 300);

  submitBtn.disabled = true;

  try {
    let resp;
    if (existingComment) {
      // FR-18: edit — PUT /api/comments/:id
      resp = await api("PUT", `/api/comments/${encodeURIComponent(existingComment.id)}`, { body });
    } else {
      // FR-21: anchor passed opaquely to server
      resp = await api("POST", "/api/comments", { anchor, body });
    }

    if (!resp.ok) {
      const msg = (resp.payload && resp.payload.error) || `HTTP ${resp.status}`;
      if (resp.status === 422) {
        // Validation error from server — show inline
        errorEl.textContent = `Validation error: ${msg}`;
        errorEl.hidden = false;
      } else {
        // FR-24: persistent save-failure banner; mark comment unsaved
        const commentId = existingComment ? existingComment.id : null;
        STATE.saveFailures.push({ commentId, message: msg });
        showBanner("save-failure", "Comment could not be saved — check disk space and permissions.");
        if (existingComment) {
          markCommentUnsaved(existingComment.id);
        }
        updateDoneButton();
      }
      return;
    }

    // Success — update local state
    STATE.pendingWrites = resp.payload.pending_writes != null ? resp.payload.pending_writes : STATE.pendingWrites;

    if (existingComment) {
      const idx = STATE.comments.findIndex(c => c.id === existingComment.id);
      if (idx >= 0) {
        STATE.comments[idx] = resp.payload.comment;
      }
    } else {
      STATE.comments.push(resp.payload.comment);
    }

    discardInput(blockNode);
    renderDoc();
    renderComments();
    updateDoneButton();
  } catch (err) {
    // Network error — treat as save failure
    STATE.saveFailures.push({ commentId: existingComment ? existingComment.id : null, message: String(err) });
    showBanner("save-failure", "Comment could not be saved — network error.");
    updateDoneButton();
  } finally {
    clearTimeout(spinnerTimer);
    const sp = submitBtn.querySelector(".comment-submit-spinner");
    if (sp) sp.remove();
    submitBtn.disabled = false;
  }
}

// ---- Comment list rendering (FR-11, FR-18, FR-19, FR-20, FR-28) ----
function renderComments() {
  commentsEl.innerHTML = "";

  // "Hide applied" toggle — default on
  if (window._hideApplied === undefined) window._hideApplied = true;

  const toolbar = document.createElement("div");
  toolbar.className = "comments-toolbar";
  const toggle = document.createElement("label");
  toggle.style.cssText = "font-size:12px;color:#555;cursor:pointer;";
  const cb = document.createElement("input");
  cb.type = "checkbox";
  cb.checked = window._hideApplied;
  cb.style.marginRight = "4px";
  cb.addEventListener("change", () => {
    window._hideApplied = cb.checked;
    renderComments();
  });
  toggle.appendChild(cb);
  toggle.appendChild(document.createTextNode("Hide applied"));
  toolbar.appendChild(toggle);
  commentsEl.appendChild(toolbar);

  // Filter comments (respect hide-applied toggle)
  const visibleComments = STATE.comments.filter(c => !(window._hideApplied && c.applied));

  if (visibleComments.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No comments yet. Hover any block and click the comment icon to add one.";
    commentsEl.appendChild(empty);
    return;
  }

  // Group visible comments by block anchor key
  const byAnchor = new Map();
  for (const c of visibleComments) {
    const k = anchorKey(c.anchor);
    if (!byAnchor.has(k)) byAnchor.set(k, []);
    byAnchor.get(k).push(c);
  }

  // FR-11, FR-20: render in document order, anchored to their blocks
  const renderedAnchorKeys = new Set();
  for (const block of STATE.blocks) {
    const k = anchorKey(block.anchor);
    if (!byAnchor.has(k)) continue;
    renderedAnchorKeys.add(k);

    const section = document.createElement("section");
    section.className = "comment-section";

    const heading = document.createElement("h2");
    // Use the block anchor's preview text (truncated) as the section label
    heading.textContent = (block.anchor.preview || "Block").slice(0, 60);
    section.appendChild(heading);

    for (const comment of byAnchor.get(k)) {
      section.appendChild(renderCommentCard(comment));
    }
    commentsEl.appendChild(section);
  }

  // FR-28: comments whose anchors are not in STATE.blocks are orphans
  const orphanComments = [];
  for (const [k, group] of byAnchor) {
    if (!renderedAnchorKeys.has(k)) orphanComments.push(...group);
  }
  if (orphanComments.length > 0) {
    renderOrphansSection(orphanComments);
  }
}

function renderCommentCard(comment) {
  const card = document.createElement("div");
  card.className = "comment-card";
  card.dataset.commentId = comment.id;

  if (comment.applied) card.classList.add("applied");
  // FR-24: mark unsaved if in saveFailures
  if (STATE.saveFailures.find(f => f.commentId === comment.id)) {
    card.classList.add("unsaved");
  }

  // Meta row: timestamp + short id
  const meta = document.createElement("div");
  meta.className = "meta";
  const timeEl = document.createElement("span");
  timeEl.textContent = comment.updated_at || comment.created_at || "";
  const idEl = document.createElement("span");
  idEl.textContent = comment.id ? comment.id.slice(0, 8) : "";
  meta.appendChild(timeEl);
  meta.appendChild(idEl);

  const bodyEl = document.createElement("div");
  bodyEl.className = "body";
  bodyEl.textContent = comment.body;

  // FR-18, FR-19: Edit and Delete buttons
  const actions = document.createElement("div");
  actions.className = "actions";

  const editBtn = document.createElement("button");
  editBtn.textContent = "Edit";
  editBtn.addEventListener("click", () => {
    // Find the corresponding block node in the doc pane
    const k = anchorKey(comment.anchor);
    const blockNode = docEl.querySelector(`.block[data-anchor="${CSS.escape(k)}"]`);
    if (blockNode) {
      openCommentInput(comment.anchor, blockNode, comment);
    }
  });

  const delBtn = document.createElement("button");
  delBtn.textContent = "Delete";
  delBtn.addEventListener("click", () => deleteComment(comment.id));

  actions.appendChild(editBtn);
  actions.appendChild(delBtn);

  card.appendChild(meta);
  card.appendChild(bodyEl);
  card.appendChild(actions);
  return card;
}

// FR-19: delete comment
async function deleteComment(id) {
  if (!confirm("Delete this comment?")) return;
  const { ok, status, payload } = await api("DELETE", `/api/comments/${encodeURIComponent(id)}`);
  if (!ok) {
    if (status !== 409) {
      showBanner("save-failure", "Comment could not be deleted.");
    }
    return;
  }
  STATE.comments = STATE.comments.filter(c => c.id !== id);
  // Remove from saveFailures too if present
  STATE.saveFailures = STATE.saveFailures.filter(f => f.commentId !== id);
  if (payload && payload.pending_writes != null) {
    STATE.pendingWrites = payload.pending_writes;
  }
  renderDoc();
  renderComments();
  updateDoneButton();
}

function markCommentUnsaved(id) {
  // Re-render the comments pane to apply the .unsaved class
  renderComments();
}

// FR-28: orphaned comments section
function renderOrphansSection(orphans) {
  const section = document.createElement("section");
  section.className = "orphans-section";

  const heading = document.createElement("h2");
  heading.textContent = `Orphaned (${orphans.length})`;
  section.appendChild(heading);

  for (const c of orphans) {
    const card = document.createElement("div");
    card.className = "comment-card orphan-card";
    const preview = (c.anchor && c.anchor.preview) ? c.anchor.preview : "?";
    const bodyPreview = c.body ? c.body.slice(0, 100) : "";
    card.textContent = `${preview} — ${bodyPreview}`;
    section.appendChild(card);
  }

  commentsEl.appendChild(section);
}

// ---- Banners (FR-08, FR-24) ----
function showBanner(kind, message) {
  // Reuse an existing banner of the same kind rather than stacking duplicates.
  let banner = bannersEl.querySelector(`.banner-${kind}`);
  if (!banner) {
    banner = document.createElement("div");
    banner.className = `banner banner-${kind}`;
    bannersEl.appendChild(banner);
  }
  // Clear previous contents
  banner.textContent = "";

  const text = document.createTextNode(message + " ");
  banner.appendChild(text);

  if (kind === "save-failure") {
    // FR-24: Acknowledge button clears banner and unblocks Done
    const ack = document.createElement("button");
    ack.className = "ack-btn";
    ack.textContent = "Acknowledge";
    ack.addEventListener("click", () => {
      banner.remove();
      STATE.saveFailures = [];
      updateDoneButton();
      renderComments(); // remove .unsaved styling
    });
    banner.appendChild(ack);
  } else if (kind === "mtime") {
    // FR-08: Reload button refetches document
    const reload = document.createElement("button");
    reload.className = "reload-btn";
    reload.textContent = "Reload";
    reload.addEventListener("click", () => reloadDoc());
    banner.appendChild(reload);
  }
}

function clearBanner(kind) {
  const banner = bannersEl.querySelector(`.banner-${kind}`);
  if (banner) banner.remove();
}

// FR-08: reload preserves existing comments; refetches document blocks + mtime
async function reloadDoc() {
  await loadDocument();
  STATE.sourceChanged = false;
  clearBanner("mtime");
}

// ---- mtime poll (FR-08) ----
async function checkMtime() {
  if (STATE.sourceChanged) return; // already showing banner; don't flood API
  let result;
  try {
    result = await api("GET", "/api/document/changed");
  } catch (_) {
    return; // network error — ignore silently
  }
  if (result.ok && result.payload && result.payload.changed) {
    STATE.sourceChanged = true;
    showBanner("mtime", "Source file changed on disk. Anchors added after this point may be unstable.");
  }
}

// ---- Done button (FR-04, FR-24) ----
function updateDoneButton() {
  const blocked = STATE.pendingWrites > 0 || STATE.saveFailures.length > 0;
  doneBtn.disabled = blocked;
  doneBtn.classList.toggle("is-saving", blocked);
  doneBtn.textContent = blocked ? "Saving…" : "Done";
}

async function clickDone() {
  doneBtn.disabled = true;
  doneBtn.classList.add("is-saving");
  doneBtn.textContent = "Saving…";
  try {
    const { ok, payload } = await api("POST", "/api/done", {});
    if (ok) {
      // FR-28: render orphans returned from the Done payload
      if (payload && payload.orphans && payload.orphans.length > 0) {
        renderOrphansSection(payload.orphans);
      }
      // Replace page — server has shut down
      document.body.innerHTML =
        '<div style="padding:32px;font:16px/1.5 -apple-system,sans-serif;">' +
        "<h1>Server stopped</h1>" +
        "<p>You can close this tab. Returning to the terminal will show the next-turn prompt.</p>" +
        "</div>";
    } else {
      const msg = (payload && payload.error) || "server error";
      showBanner("save-failure", "Done could not complete: " + msg);
      updateDoneButton();
    }
  } catch (_) {
    // Connection reset is expected when server shuts down — treat as success.
    document.body.innerHTML =
      '<div style="padding:32px;font:16px/1.5 -apple-system,sans-serif;">' +
      "<h1>Server stopped</h1>" +
      "</div>";
  }
}

// ---- Discard confirm modal (FR-16) ----
function confirmDiscard() {
  return new Promise(resolve => {
    const modal = document.createElement("div");
    modal.className = "discard-confirm";

    const dialog = document.createElement("div");
    dialog.className = "dialog";

    const msg = document.createElement("div");
    msg.textContent = "Discard this draft comment?";

    const actionsDiv = document.createElement("div");
    actionsDiv.className = "actions";

    const keepBtn = document.createElement("button");
    keepBtn.textContent = "Keep editing";
    keepBtn.addEventListener("click", () => { modal.remove(); resolve(false); });

    const discardBtn = document.createElement("button");
    discardBtn.textContent = "Discard";
    discardBtn.addEventListener("click", () => { modal.remove(); resolve(true); });

    actionsDiv.appendChild(keepBtn);
    actionsDiv.appendChild(discardBtn);
    dialog.appendChild(msg);
    dialog.appendChild(actionsDiv);
    modal.appendChild(dialog);
    document.body.appendChild(modal);

    // Also allow Escape to keep editing (don't lose the draft via modal)
    modal.addEventListener("keydown", e => {
      if (e.key === "Escape") { modal.remove(); resolve(false); }
    });
    // Focus the discard button so keyboard nav works naturally
    discardBtn.focus();
  });
}

// ---- Wire-up on DOMContentLoaded ----
document.addEventListener("DOMContentLoaded", () => {
  docEl      = document.getElementById("doc");
  commentsEl = document.getElementById("comments");
  bannersEl  = document.getElementById("banners");
  doneBtn    = document.getElementById("done-btn");
  blockTpl   = document.getElementById("block-template");
  inputTpl   = document.getElementById("comment-input-template");

  doneBtn.addEventListener("click", clickDone);

  // FR-08: check mtime lazily on first user interaction (not on a timer).
  // Using { once: true } on mousemove gives one check per page focus — cheap.
  document.addEventListener("mousemove", checkMtime, { once: true });
  document.addEventListener("focusin", checkMtime, { once: true });

  loadDocument();
});
