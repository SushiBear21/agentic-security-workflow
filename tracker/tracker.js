"use strict";

const byId = (id) => document.getElementById(id);
const status = byId("status");
let token = "";
let session;
let submissionId;

async function request(path, body) {
  const headers = { Authorization: "Bearer " + token };
  const options = { headers };
  if (body) {
    headers["Content-Type"] = "application/json";
    Object.assign(options, { method: "POST", body: JSON.stringify(body) });
  }
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error);
  return value;
}

function onSubmit(form, task) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button");
    button.disabled = true;
    status.textContent = "";
    try {
      await task();
    } catch (error) {
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

function add(parent, tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  parent.append(node);
}

function reviewForm(card, item) {
  const form = document.createElement("form");
  // Markup is static. Evidence and persona fields are always set as text.
  form.innerHTML = '<label>Decision<select><option value="approve">Approve</option><option value="reject">Reject</option></select></label>' +
    '<label>Review rationale<input required maxlength="500"></label><button>Record decision</button>';
  onSubmit(form, async () => {
    const decision = form.querySelector("select").value;
    const reason = form.querySelector("input").value;
    await request("/api/review", { id: item.id, sha256: item.sha256, decision, reason });
    await refresh();
    status.textContent = "Decision recorded.";
  });
  card.append(form);
}

async function refresh() {
  const items = await request("/api/evidence");
  const records = byId("records");
  records.replaceChildren();
  if (!items.length) add(records, "p", "No evidence submitted yet.");
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "panel";
    add(card, "h3", item.title);
    add(card, "p", item.status + " · Submitted by " + item.submitted_by + " · " + item.id, "meta");
    add(card, "p", item.note);
    if (item.reviewed_by) add(card, "p", "Reviewed by " + item.reviewed_by + " · " + item.reason, "meta");
    if (session.role === "reviewer" && item.status === "pending") reviewForm(card, item);
    records.append(card);
  }
}

onSubmit(byId("sign-in"), async () => {
  token = byId("token").value.trim();
  session = await request("/api/session");
  await refresh();
  byId("token").value = "";
  byId("workspace-name").textContent = session.workspace + " workspace · " + session.name;
  byId("sign-in").hidden = true;
  byId("sign-out").hidden = false;
  byId("workspace").hidden = false;
  byId("submission").hidden = session.role !== "contributor";
  byId("export").hidden = session.role !== "reviewer";
});

byId("sign-out").addEventListener("click", () => window.location.reload());

for (const field of ["title", "note"]) {
  byId(field).addEventListener("input", () => { submissionId = undefined; });
}

onSubmit(byId("submission"), async () => {
  submissionId ??= crypto.randomUUID();
  await request("/api/evidence", { id: submissionId, title: byId("title").value, note: byId("note").value });
  byId("submission").reset();
  submissionId = undefined;
  await refresh();
  status.textContent = "Evidence submitted for review.";
});

byId("export").addEventListener("click", async () => {
  const button = byId("export");
  button.disabled = true;
  try {
    const record = await request("/api/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "evidence-audit.json";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    status.textContent = "Audit export generated.";
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
