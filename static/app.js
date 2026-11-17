"use strict";
// Interface de démonstration. Tout texte venant de l'API est inséré comme texte brut (textContent) : anti-XSS.
const $ = (id) => document.getElementById(id);
let token = sessionStorage.getItem("token");
let selected = null;

function say(text, ok) {
  const m = $("msg");
  m.textContent = text;
  m.className = ok ? "ok" : "err";
  m.hidden = false;
}

async function api(path, { method = "GET", body, headers = {} } = {}) {
  const h = { "Content-Type": "application/json", ...headers };
  if (token) h.Authorization = "Bearer " + token;
  const res = await fetch(path, { method, headers: h, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const e = data.error || {};
    const extra = (e.details || []).map((d) => d.message).join(" ");
    throw new Error(`${e.code || res.status} — ${e.message || "Erreur"} ${extra}`.trim());
  }
  return data;
}

function cell(tr, text, cls) {
  const td = document.createElement("td");
  td.textContent = text;
  if (cls) td.className = cls;
  tr.appendChild(td);
}

async function refresh() {
  const accounts = await api("/api/accounts");
  const tbody = document.querySelector("#accounts tbody");
  tbody.replaceChildren();
  for (const a of accounts) {
    const tr = document.createElement("tr");
    tr.dataset.id = a.id;
    if (selected && selected.id === a.id) { tr.className = "sel"; selected = a; }
    cell(tr, a.iban); cell(tr, a.type === "CHECKING" ? "Courant" : "Épargne"); cell(tr, a.status); cell(tr, a.balance, "num");
    tr.addEventListener("click", () => { selected = a; refresh().then(loadHistory); });
    tbody.appendChild(tr);
  }
  $("detail").hidden = !selected;
  if (selected) {
    $("detail-title").textContent = `${selected.type === "CHECKING" ? "Compte courant" : "Compte épargne"} · ${selected.iban}`;
    $("projection").hidden = selected.type !== "SAVINGS";
  }
}

async function loadHistory() {
  if (!selected) return;
  const page = await api(`/api/accounts/${selected.id}/transactions?limit=20`);
  const tbody = document.querySelector("#history tbody");
  tbody.replaceChildren();
  for (const t of page.items) {
    const tr = document.createElement("tr");
    cell(tr, t.created_at.replace("T", " ").slice(0, 19)); cell(tr, t.type);
    cell(tr, [t.counterparty_iban, t.reference].filter(Boolean).join(" · "));
    cell(tr, t.amount, "num"); cell(tr, t.balance_after, "num");
    tbody.appendChild(tr);
  }
}

function showApp(on) {
  $("auth").hidden = on; $("app").hidden = !on; $("logout").hidden = !on;
  if (!on) { $("who").textContent = ""; selected = null; }
}

async function start() {
  if (!token) return showApp(false);
  try {
    const me = await api("/api/auth/me");
    $("who").textContent = `${me.full_name} (${me.role})`;
    showApp(true);
    await refresh();
  } catch (e) {
    token = null; sessionStorage.removeItem("token"); showApp(false);
  }
}

function form(id, handler) {
  $(id).addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = Object.fromEntries(new FormData(ev.target).entries());
    try { await handler(fd, ev.target); } catch (e) { say(e.message, false); }
  });
}

form("login-form", async (fd) => {
  const r = await api("/api/auth/login", { method: "POST", body: fd });
  token = r.access_token; sessionStorage.setItem("token", token);
  $("msg").hidden = true; await start();
});
form("register-form", async (fd, f) => {
  await api("/api/auth/register", { method: "POST", body: fd });
  f.reset(); say("Compte client créé. Vous pouvez vous connecter.", true);
});
form("deposit-form", async (fd, f) => {
  await api(`/api/accounts/${selected.id}/deposit`, { method: "POST", body: { amount: fd.amount } });
  f.reset(); say("Dépôt effectué.", true); await refresh(); await loadHistory();
});
form("withdraw-form", async (fd, f) => {
  await api(`/api/accounts/${selected.id}/withdraw`, { method: "POST", body: { amount: fd.amount } });
  f.reset(); say("Retrait effectué.", true); await refresh(); await loadHistory();
});
form("transfer-form", async (fd, f) => {
  const key = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now()) + Math.random();
  const body = { from_account_id: selected.id, to_iban: fd.to_iban, amount: fd.amount, reference: fd.reference || null };
  const r = await api("/api/transfers", { method: "POST", body, headers: { "Idempotency-Key": key } });
  f.reset(); say(`Virement effectué (frais : ${r.fee} TND).`, true); await refresh(); await loadHistory();
});

$("open-account").addEventListener("click", async () => {
  try { await api("/api/accounts", { method: "POST", body: { type: $("new-type").value } }); say("Compte ouvert.", true); await refresh(); }
  catch (e) { say(e.message, false); }
});
$("close-account").addEventListener("click", async () => {
  try { await api(`/api/accounts/${selected.id}/close`, { method: "POST" }); say("Compte clôturé.", true); await refresh(); await loadHistory(); }
  catch (e) { say(e.message, false); }
});
$("projection").addEventListener("click", async () => {
  try {
    const p = await api(`/api/accounts/${selected.id}/interest-projection?days=30`);
    say(`Projection sur ${p.days} jours : +${p.projected_interest} TND (taux ${p.annual_rate}).`, true);
  } catch (e) { say(e.message, false); }
});
$("logout").addEventListener("click", () => { token = null; sessionStorage.removeItem("token"); showApp(false); });

start();
