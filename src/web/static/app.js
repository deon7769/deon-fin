// ---------------------------------------------------------------- utilities
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function api(method, path, body) {
  const resp = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
  return data;
}

function setStatus(el, text, klass) {
  el.className = `status ${klass || ""}`;
  el.textContent = text;
}

function fmtBRL(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" })
    .format(value || 0);
}

// ---------------------------------------------------------------- tabs
function switchTab(name) {
  $$(".tab-content").forEach((el) => el.classList.remove("active"));
  $$(".tab-btn").forEach((el) => el.classList.remove("active"));
  $(`#tab-${name}`).classList.add("active");
  $(`.tab-btn[data-tab="${name}"]`).classList.add("active");
  if (name === "config") {
    refreshItems();
    refreshSummary();
    refreshSyncStatus();
  } else if (name === "maintenance" && !maintLoaded) {
    loadMaintenance();
  } else if (name === "simulador") {
    $("#sim-sobra").value = Math.max(0, Math.round(lastSobra));
  } else if (name === "cartao") {
    loadCartao();
  }
}
$$(".tab-btn").forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));

// ---------------------------------------------------------------- dashboard
const CHART_COLORS = [
  "#7c5cff", "#36a2eb", "#4ade80", "#f59e0b", "#f87171",
  "#22d3ee", "#e879f9", "#a3e635", "#fb923c", "#94a3b8", "#2dd4bf", "#fbbf24",
];
let chartFluxo = null;
let chartCategorias = null;
let chartFuturosMes = null;

if (window.Chart) {
  Chart.defaults.color = "#8a8f9b";
  Chart.defaults.borderColor = "#262a33";
  Chart.defaults.font.family =
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif";
}

async function loadDashboard(meses) {
  let d;
  const qs = meses ? `?meses=${meses}` : "";
  try {
    d = await api("GET", "/api/dashboard" + qs);
  } catch (e) {
    console.error("dashboard:", e);
    return;
  }
  renderKPIs(d.kpis);
  renderExecutivo(d.executivo);
  renderFluxo(d.fluxo_mensal);
  renderCategorias(d.gasto_por_categoria);
  renderBudget(d.budget_5030);
  renderFuturos(d.compromissos_futuros);
  renderRecorrencias(d.recorrencias);
  renderCusto(d.custo_financeiro);
  renderWishlist(d.wishlist);
  lastSobra = (d.kpis.renda_informada || d.kpis.renda_media || 0) - (d.kpis.gasto_medio || 0);

  if (d.perfil_familiar) {
    $("#family-section").style.display = "block";
    renderFamily(d.perfil_familiar);
  } else {
    $("#family-section").style.display = "none";
  }
}

function renderFamily(pf) {
  // Ativos / Passivos / Patrimônio Líquido
  const pc = pf.patrimonio_consolidado;
  $("#family-ativos").textContent = fmtBRL(pc.total_ativos);
  $("#family-passivos").textContent = fmtBRL(pc.total_passivos);
  $("#family-patrimonio-liquido").textContent = fmtBRL(pc.patrimonio_liquido);

  // Imóvel (nome vem do perfil familiar, não fica fixo no código)
  if (pf.fluxo_imoveis && pf.fluxo_imoveis.length > 0) {
    const im = pf.fluxo_imoveis[0];
    const nomeEl = document.getElementById("imovel-nome");
    if (nomeEl && im.nome) nomeEl.textContent = im.nome;
    $("#imovel-receita").textContent = fmtBRL(im.receita);
    $("#imovel-financiamento").textContent = fmtBRL(im.custos.financiamento);
    $("#imovel-condominio").textContent = fmtBRL(im.custos.condominio);
    $("#imovel-iptu").textContent = fmtBRL(im.custos.iptu_lixo);
    $("#imovel-resultado").textContent = fmtBRL(im.resultado);
  }

  // Caixa e Investimentos
  const caixasTb = $("#family-caixa-rows");
  caixasTb.innerHTML = "";
  if (pf.investimentos_caixa && pf.investimentos_caixa.length > 0) {
    for (const c of pf.investimentos_caixa) {
      const aporte = c.aporte_mensal_recorrente ? fmtBRL(c.aporte_mensal_recorrente) : "—";
      caixasTb.insertAdjacentHTML(
        "beforeend",
        `<tr><td>${c.local}</td><td>${aporte}</td><td class="num">${fmtBRL(c.valor)}</td></tr>`
      );
    }
  } else {
    caixasTb.innerHTML = `<tr><td colspan="3" class="muted">Nenhum caixa ou investimento cadastrado.</td></tr>`;
  }

  // Provisões
  const provsBox = $("#provisoes-list");
  provsBox.innerHTML = "";
  $("#provisoes-total-mensal").textContent = `${fmtBRL(pf.provisoes_total_mensal)}/mês`;
  
  if (pf.provisoes && pf.provisoes.length > 0) {
    for (const p of pf.provisoes) {
      const el = document.createElement("div");
      el.className = "budget-bar-group";
      const details = p.proxima_ocorrencia ? ` (Próxima: ${p.proxima_ocorrencia})` : "";
      el.innerHTML = `
        <div class="bar-label">
          <span>${p.nome}<span class="muted small">${details}</span></span>
          <strong>${fmtBRL(p.mensal)}/mês <span class="muted small">(Alvo: ${fmtBRL(p.alvo)})</span></strong>
        </div>
        <div class="progress-bg">
          <div class="progress-fill fill-good" style="width: 100%"></div>
        </div>`;
      provsBox.appendChild(el);
    }
  } else {
    provsBox.innerHTML = `<p class="muted">Nenhuma provisão configurada.</p>`;
  }

  // Metas
  const metasBox = $("#metas-list");
  metasBox.innerHTML = "";
  if (pf.metas && pf.metas.length > 0) {
    for (const m of pf.metas) {
      const alvo = m.alvo || 1;
      const atual = m.atual || 0;
      let realAtual = atual;
      if (m.nome === "Reserva de Caixa Familiar" && pc.detalhe_ativos.caixas_investimentos) {
        realAtual = pc.detalhe_ativos.caixas_investimentos;
      }
      let realPct = Math.round((realAtual / alvo) * 100);
      realPct = Math.max(0, Math.min(realPct, 100));
      
      const el = document.createElement("div");
      el.className = "budget-bar-group";
      el.innerHTML = `
        <div class="bar-label">
          <span>${m.nome} <span class="muted small">(Prazo: ${m.prazo || "—"})</span></span>
          <strong>${realPct}% · ${fmtBRL(realAtual)} de ${fmtBRL(alvo)}</strong>
        </div>
        <div class="progress-bg">
          <div class="progress-fill fill-good" style="width: ${realPct}%"></div>
        </div>`;
      metasBox.appendChild(el);
    }
  } else {
    metasBox.innerHTML = `<p class="muted">Nenhuma meta configurada.</p>`;
  }
}

function renderKPIs(k) {
  const renda = k.renda_informada || k.renda_media;
  $("#kpi-renda").textContent = fmtBRL(renda);
  $("#kpi-gasto").textContent = fmtBRL(k.gasto_medio);
  $("#kpi-saldo").textContent = fmtBRL(renda - k.gasto_medio);
  $("#kpi-saldo").className = renda - k.gasto_medio >= 0 ? "good" : "bad";
  $("#kpi-investido").textContent = fmtBRL(k.investido_total);
  $("#kpi-futuro").textContent = fmtBRL(k.compromissos_futuros);
}

function renderExecutivo(ex) {
  if (!ex) return;
  if (ex.frase) $("#frase-resumo").textContent = ex.frase;
  const op = $("#kpi-saldo-op");
  op.textContent = fmtBRL(ex.saldo_operacional);
  op.className = ex.saldo_operacional >= 0 ? "good" : "bad";
  const pat = $("#kpi-saldo-pat");
  pat.textContent = fmtBRL(ex.saldo_patrimonial);
  pat.className = ex.saldo_patrimonial >= 0 ? "good" : "bad";
}

function renderFluxo(fluxo) {
  const ctx = $("#chartFluxo");
  if (chartFluxo) chartFluxo.destroy();
  chartFluxo = new Chart(ctx, {
    type: "bar",
    data: {
      labels: fluxo.map((m) => m.mes),
      datasets: [
        { label: "Renda", data: fluxo.map((m) => m.renda), backgroundColor: "#4ade80" },
        { label: "Gasto", data: fluxo.map((m) => m.gasto), backgroundColor: "#f87171" },
        { label: "Investido", data: fluxo.map((m) => m.investido), backgroundColor: "#7c5cff" },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderCategorias(cats) {
  const ctx = $("#chartCategorias");
  if (chartCategorias) chartCategorias.destroy();
  chartCategorias = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: cats.map((c) => c.categoria),
      datasets: [{ data: cats.map((c) => c.total), backgroundColor: CHART_COLORS }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "right", labels: { boxWidth: 12 } } },
    },
  });
}

const BUDGET_LABELS = {
  essencial: "Essenciais",
  desejos: "Desejos",
  financeiro: "Poupança / Dívida",
};

function renderBudget(b) {
  $("#budget-base").textContent = `(base: renda ${fmtBRL(b.renda)}/mês)`;
  const box = $("#budget-bars");
  box.innerHTML = "";
  for (const key of ["essencial", "desejos", "financeiro"]) {
    const blk = b.blocos[key];
    // Para essenciais/desejos, passar da meta é ruim; para financeiro, é bom.
    const over = blk.pct_renda > blk.meta_pct;
    const good = key === "financeiro" ? over : !over;
    const width = Math.min(blk.pct_renda, 100);
    const el = document.createElement("div");
    el.className = "budget-bar-group";
    el.innerHTML = `
      <div class="bar-label">
        <span>${BUDGET_LABELS[key]} <span class="muted small">(meta ${blk.meta_pct}%)</span></span>
        <strong class="${good ? "good" : "bad"}">${blk.pct_renda}% · ${fmtBRL(blk.valor_mensal)}</strong>
      </div>
      <div class="progress-bg">
        <div class="progress-fill ${good ? "fill-good" : "fill-bad"}" style="width:${width}%"></div>
        <div class="meta-mark" style="left:${Math.min(blk.meta_pct, 100)}%"></div>
      </div>`;
    box.appendChild(el);
  }
}

function renderFuturos(f) {
  $("#futuros-total").textContent = fmtBRL(f.total);
  // gráfico por mês
  const ctx = $("#chartFuturosMes");
  if (chartFuturosMes) chartFuturosMes.destroy();
  const pm = f.por_mes || [];
  if (ctx && pm.length) {
    chartFuturosMes = new Chart(ctx, {
      type: "bar",
      data: {
        labels: pm.map((x) => x.mes),
        datasets: [{ label: "A vencer", data: pm.map((x) => x.total), backgroundColor: "#f59e0b" }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } },
      },
    });
  }
  const tb = $("#futuros-rows");
  tb.innerHTML = "";
  if (!f.por_categoria.length) {
    tb.innerHTML = `<tr><td colspan="2" class="muted">Nenhum compromisso futuro.</td></tr>`;
    return;
  }
  for (const row of f.por_categoria) {
    tb.insertAdjacentHTML(
      "beforeend",
      `<tr><td>${row.categoria}</td><td class="num">${fmtBRL(row.total)}</td></tr>`
    );
  }
}

function renderRecorrencias(rows) {
  const tb = $("#recorrencias-rows");
  tb.innerHTML = "";
  if (!rows.length) {
    tb.innerHTML = `<tr><td colspan="3" class="muted">Nenhuma recorrência identificada.</td></tr>`;
    return;
  }
  for (const r of rows) {
    const tipo = r.tipo || (r.estavel ? "assinatura" : "recorrencia");
    const cls = tipo === "assinatura" ? "badge badge-sub" : "badge";
    const badge = `<span class="${cls}">${tipo}</span>`;
    tb.insertAdjacentHTML(
      "beforeend",
      `<tr><td>${r.comerciante} ${badge}</td><td>${r.meses}</td>
       <td class="num">${fmtBRL(r.valor_medio)}</td></tr>`
    );
  }
}

function renderCusto(c) {
  $("#custo-total").textContent = fmtBRL(c.total);
  const tb = $("#custo-rows");
  tb.innerHTML = "";
  for (const [cat, val] of Object.entries(c.por_categoria || {})) {
    tb.insertAdjacentHTML(
      "beforeend",
      `<tr><td>${cat}</td><td class="num">${fmtBRL(val)}</td></tr>`
    );
  }
}

let lastSobra = 0;

function renderWishlist(w) {
  const box = $("#wishlist-list");
  if (!box) return;
  box.innerHTML = "";
  const resumo = $("#wishlist-resumo");
  if (!w || !w.itens || !w.itens.length) {
    box.innerHTML = `<p class="muted">Nenhum desejo cadastrado. Adicione na aba Manutenção.</p>`;
    if (resumo) resumo.textContent = "";
    return;
  }
  if (resumo) {
    const folgaCls = w.folga >= 0 ? "good" : "bad";
    resumo.innerHTML = `— guardar <strong>${fmtBRL(w.total_guardar_mes)}/mês</strong> · sobra <span class="${folgaCls}">${fmtBRL(w.sobra_mensal)}</span>`;
  }
  for (const it of w.itens) {
    const cls = it.cabe_na_sobra ? "fill-good" : "fill-bad";
    const el = document.createElement("div");
    el.className = "budget-bar-group";
    el.innerHTML = `
      <div class="bar-label">
        <span>${it.nome} <span class="muted small">(${it.prazo_meses}m · ${fmtBRL(it.valor_alvo)})</span></span>
        <strong>${fmtBRL(it.guardar_mes)}/mês · ${it.progresso_pct}%</strong>
      </div>
      <div class="progress-bg">
        <div class="progress-fill ${cls}" style="width:${Math.min(it.progresso_pct, 100)}%"></div>
      </div>`;
    box.appendChild(el);
  }
}

// ---------------------------------------------------------------- connect (config)
async function openConnectWidget({ itemId } = {}) {
  const statusEl = $("#connect-status");
  setStatus(statusEl, "Gerando token...");
  let token;
  try {
    const r = await api("POST", "/api/connect-token", {
      client_user_id: "local-user",
      item_id: itemId,
    });
    token = r.accessToken;
  } catch (e) {
    setStatus(statusEl, `Falha ao gerar token: ${e.message}`, "err");
    return;
  }
  setStatus(statusEl, "Abrindo widget...");
  const pluggy = new PluggyConnect({
    connectToken: token,
    includeSandbox: false,
    onSuccess: async (itemData) => {
      const item = itemData.item || itemData;
      setStatus(statusEl, `Conectado: ${item.connector?.name || item.id}. Sincronizando...`, "ok");
      try {
        await api("POST", "/api/items", {
          item_id: item.id,
          connector_id: item.connector?.id,
          connector_name: item.connector?.name,
          status: item.status,
          client_user_id: "local-user",
        });
      } catch (e) {
        setStatus(statusEl, `Conectou mas falhou ao registrar: ${e.message}`, "err");
        return;
      }
      await refreshItems();
      setTimeout(() => { refreshSummary(); loadDashboard(); }, 5000);
    },
    onError: (err) => setStatus(statusEl, `Erro: ${err.message || err}`, "err"),
    onClose: () => {
      if (!statusEl.classList.contains("ok") && !statusEl.classList.contains("err")) {
        setStatus(statusEl, "Widget fechado sem conectar.");
      }
    },
  });
  pluggy.init();
}

async function refreshItems() {
  const tbody = $("#items-table tbody");
  tbody.innerHTML = "";
  let items;
  try {
    items = await api("GET", "/api/items");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5">Erro: ${e.message}</td></tr>`;
    return;
  }
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="muted">Nenhum item conectado ainda.</td></tr>`;
    return;
  }
  for (const it of items) {
    tbody.insertAdjacentHTML("beforeend", `
      <tr>
        <td><code>${it.id.slice(0, 8)}…</code></td>
        <td>${it.connector_name || "—"}</td>
        <td>${it.status || "—"}</td>
        <td>${it.last_synced_at || "<em>nunca</em>"}</td>
        <td>
          <button class="secondary" data-action="sync"   data-id="${it.id}">Sync</button>
          <button class="secondary" data-action="update" data-id="${it.id}">Atualizar credenciais</button>
          <button class="danger"    data-action="delete" data-id="${it.id}">Remover</button>
        </td>
      </tr>`);
  }
}

$("#items-table").addEventListener("click", async (ev) => {
  const btn = ev.target.closest("button");
  if (!btn) return;
  const { action, id } = btn.dataset;
  if (action === "sync") {
    btn.disabled = true; btn.textContent = "Sincronizando…";
    try { await api("POST", `/api/items/${id}/sync`, { days: 90 }); }
    finally { btn.disabled = false; btn.textContent = "Sync"; }
    setTimeout(() => { refreshSummary(); loadDashboard(); }, 4000);
  } else if (action === "update") {
    await openConnectWidget({ itemId: id });
  } else if (action === "delete") {
    if (!confirm("Remover essa conexão? As transações já importadas continuam no banco local.")) return;
    await api("DELETE", `/api/items/${id}`);
    await refreshItems();
  }
});

async function refreshSummary() {
  const tbody = $("#summary-table tbody");
  const totals = $("#summary-totals");
  tbody.innerHTML = "";
  totals.innerHTML = "";
  let s;
  try {
    s = await api("GET", "/api/summary?days=30");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="2">Erro: ${e.message}</td></tr>`;
    return;
  }
  totals.innerHTML = `
    <div class="pill inflow"><small>Entradas</small><strong>${fmtBRL(s.inflow)}</strong></div>
    <div class="pill outflow"><small>Saídas</small><strong>${fmtBRL(s.outflow)}</strong></div>
    <div class="pill"><small>Líquido</small><strong>${fmtBRL(s.net)}</strong></div>
    <div class="pill"><small>Transações</small><strong>${s.transactions}</strong></div>`;
  if (!s.by_category.length) {
    tbody.innerHTML = `<tr><td colspan="2" class="muted">Sem saídas no período.</td></tr>`;
    return;
  }
  for (const row of s.by_category) {
    tbody.insertAdjacentHTML("beforeend",
      `<tr><td>${row.category}</td><td class="num">${fmtBRL(row.amount)}</td></tr>`);
  }
}

// ---------------------------------------------------------------- auto-sync
function fmtSyncTs(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR");
}

async function refreshSyncStatus() {
  const el = $("#sync-status");
  if (!el) return;
  let s;
  try { s = await api("GET", "/api/sync-status"); }
  catch { return; }
  if (s.running) {
    el.className = "status";
    el.textContent = "Sincronizando contas…";
  } else {
    el.className = "status muted";
    const intervalo = s.auto_sync_minutes ? `a cada ${s.auto_sync_minutes} min` : "manual";
    el.textContent = `Última: ${fmtSyncTs(s.last_finished)} · ${s.last_result || "sem sync ainda"} · auto: ${intervalo}`;
  }
  return s;
}

async function syncAll() {
  const btn = $("#btn-sync-all");
  btn.disabled = true;
  try { await api("POST", "/api/sync-all"); } catch (e) { /* segue */ }
  // poll até terminar, então recarrega o dashboard
  const poll = setInterval(async () => {
    const s = await refreshSyncStatus();
    if (s && !s.running) {
      clearInterval(poll);
      btn.disabled = false;
      loadDashboard($("#dash-period").value);
    }
  }, 2500);
}

// ---------------------------------------------------------------- cartões (carrossel)
let cartaoData = null;
let cartaoIdx = 0;
const TIPO_LABEL = { realizado: "Realizado", atual: "Mês atual", futuro: "Parcelado (futuro)" };

async function loadCartao() {
  let d;
  try { d = await api("GET", "/api/cartao"); } catch (e) { return; }
  cartaoData = d;
  cartaoIdx = d.indice_atual || 0;
  $("#cartao-realizado").textContent = fmtBRL(d.resumo.gasto_realizado);
  $("#cartao-fatura").textContent = fmtBRL(d.resumo.fatura_mes_atual);
  $("#cartao-futuro").textContent = fmtBRL(d.resumo.futuro_parcelado);
  const pct = d.resumo.pct_renda_comprometida;
  const pctEl = $("#cartao-pct");
  pctEl.textContent = pct == null ? "—" : `${pct}%`;
  pctEl.className = pct != null && pct > 30 ? "bad" : "";
  renderCartaoStrip();
  renderCartaoSlide();
  renderCartaoAlertas(d.alertas || []);
  renderCartaoComerciantes(d.top_comerciantes || []);
}

function renderCartaoAlertas(alertas) {
  const card = $("#cartao-alertas-card");
  const box = $("#cartao-alertas");
  if (!alertas.length) { card.style.display = "none"; return; }
  card.style.display = "";
  box.innerHTML = alertas
    .map((a) => `<p class="alerta">⚠️ ${a.msg}</p>`)
    .join("");
}

function renderCartaoComerciantes(rows) {
  const tb = $("#cartao-comerciantes");
  tb.innerHTML = "";
  if (!rows.length) {
    tb.innerHTML = `<tr><td colspan="3" class="muted">—</td></tr>`;
    return;
  }
  for (const r of rows) {
    tb.insertAdjacentHTML(
      "beforeend",
      `<tr><td>${r.comerciante}</td><td>${r.compras}</td><td class="num">${fmtBRL(r.total)}</td></tr>`
    );
  }
}

function renderCartaoStrip() {
  const strip = $("#cartao-strip");
  strip.innerHTML = "";
  cartaoData.meses.forEach((m, i) => {
    const chip = document.createElement("button");
    chip.className = `month-chip tipo-${m.tipo}${i === cartaoIdx ? " active" : ""}`;
    chip.textContent = m.mes;
    chip.onclick = () => { cartaoIdx = i; renderCartaoStrip(); renderCartaoSlide(); };
    strip.appendChild(chip);
  });
  const active = strip.querySelector(".active");
  if (active) active.scrollIntoView({ inline: "center", block: "nearest" });
}

function renderCartaoSlide() {
  const m = cartaoData.meses[cartaoIdx];
  const slide = $("#cartao-slide");
  if (!m) { slide.innerHTML = `<p class="muted">Sem dados.</p>`; return; }
  const cats = m.por_categoria
    .map((c) => `<tr><td>${c.categoria}</td><td class="num">${fmtBRL(c.total)}</td></tr>`)
    .join("") || `<tr><td class="muted">—</td></tr>`;
  const cartoes = m.por_cartao
    .map((c) => `<span class="chip">${c.cartao}: ${fmtBRL(c.total)}</span>`)
    .join(" ") || "—";
  slide.innerHTML = `
    <div class="slide-head">
      <div><span class="badge tipo-${m.tipo}">${TIPO_LABEL[m.tipo]}</span>
        <span class="slide-month">${m.mes}</span></div>
      <div class="slide-total ${m.tipo === "futuro" ? "" : "bad"}">
        ${fmtBRL(m.total)} <span class="muted small">· ${m.transacoes} compras</span>
      </div>
    </div>
    <div class="grid-2" style="margin-top:14px;">
      <div><h3 class="muted small">Por categoria</h3>
        <table class="data-table"><tbody>${cats}</tbody></table></div>
      <div><h3 class="muted small">Por cartão</h3><div class="chips">${cartoes}</div></div>
    </div>`;
}

function cartaoMove(delta) {
  if (!cartaoData) return;
  cartaoIdx = Math.max(0, Math.min(cartaoData.meses.length - 1, cartaoIdx + delta));
  renderCartaoStrip();
  renderCartaoSlide();
}
$("#cartao-prev").addEventListener("click", () => cartaoMove(-1));
$("#cartao-next").addEventListener("click", () => cartaoMove(1));

// ---------------------------------------------------------------- analysis (IA)
function renderMarkdown(el, text) {
  el.classList.remove("muted");
  el.innerHTML = window.marked ? window.marked.parse(text) : `<pre>${text}</pre>`;
}

async function runAnalysis(kind) {
  const out = $("#analysis-output");
  const btn = $("#btn-analyze");
  btn.disabled = true;
  out.classList.add("muted");
  out.classList.remove("err");
  const t0 = Date.now();
  const timer = setInterval(() => {
    const s = Math.floor((Date.now() - t0) / 1000);
    if (!out.textContent.startsWith("Analisando")) return;
    out.textContent = `Analisando seus dados… (${s}s — modelos com raciocínio podem levar 1–2 min)`;
  }, 1000);
  out.textContent = "Analisando seus dados… (0s — modelos com raciocínio podem levar 1–2 min)";
  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind }),
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      out.className = "analysis-output err";
      out.textContent = data.detail || `HTTP ${resp.status}`;
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let text = "";
    let rendered = false;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      text += decoder.decode(value, { stream: true });
      if (text.trim()) {
        renderMarkdown(out, text);
        rendered = true;
      }
    }
    if (!rendered) {
      out.className = "analysis-output err";
      out.textContent = "Sem resposta da IA. Verifique ANALYST_MODEL e a chave de API no .env.";
    }
  } catch (e) {
    out.className = "analysis-output err";
    out.textContent = `Falha: ${e.message}`;
  } finally {
    clearInterval(timer);
    btn.disabled = false;
  }
}
$("#btn-analyze").addEventListener("click", () => runAnalysis($("#analysis-kind").value));

// ---------------------------------------------------------------- maintenance
let maintLoaded = false;
let maintFullProfile = {};

const MAINT_COLS = {
  receitas: [
    { key: "membro", label: "Membro", type: "text" },
    { key: "valor", label: "Valor (R$)", type: "number" },
  ],
  caixa: [
    { key: "local", label: "Local / Conta", type: "text" },
    { key: "valor", label: "Saldo (R$)", type: "number" },
    { key: "aporte_mensal_recorrente", label: "Aporte/mês", type: "number" },
  ],
  provisoes: [
    { key: "nome", label: "Nome", type: "text" },
    { key: "mensal", label: "Mensal", type: "number" },
    { key: "alvo", label: "Alvo", type: "number" },
    { key: "periodicidade_meses", label: "Period. (m)", type: "number" },
    { key: "proxima_ocorrencia", label: "Próxima (AAAA-MM)", type: "text" },
  ],
  metas: [
    { key: "nome", label: "Nome", type: "text" },
    { key: "alvo", label: "Alvo", type: "number" },
    { key: "atual", label: "Atual", type: "number" },
    { key: "prazo", label: "Prazo", type: "text" },
  ],
  categorias: [
    { key: "en", label: "Origem (inglês)", type: "text" },
    { key: "pt", label: "Tradução (PT)", type: "text" },
  ],
  recorrencias: [
    { key: "match", label: "Contém (comerciante)", type: "text" },
    { key: "tipo", label: "Tipo", type: "select", options: ["assinatura", "recorrencia", "ignorar"] },
    { key: "rotulo", label: "Rótulo (opcional)", type: "text" },
  ],
  wishlist: [
    { key: "nome", label: "Desejo", type: "text" },
    { key: "valor_alvo", label: "Valor alvo", type: "number" },
    { key: "prazo_meses", label: "Prazo (m)", type: "number" },
    { key: "guardado", label: "Já guardado", type: "number" },
    { key: "prioridade", label: "Prioridade", type: "number" },
  ],
  imoveis: [
    { key: "nome", label: "Imóvel", type: "text" },
    { key: "valor_mercado", label: "Valor mercado", type: "number" },
    { key: "saldo_devedor", label: "Saldo devedor", type: "number" },
    { key: "taxa_juros_anual", label: "Juros % a.a.", type: "number" },
    { key: "prazo_restante_meses", label: "Prazo (m)", type: "number" },
    { key: "aluguel_receita", label: "Aluguel", type: "number" },
    { key: "custo_financiamento", label: "Financiamento", type: "number" },
    { key: "custo_condominio", label: "Condomínio", type: "number" },
    { key: "custo_iptu_lixo", label: "IPTU/lixo", type: "number" },
  ],
};

function imovelToRow(im) {
  const c = im.custos || {};
  return {
    nome: im.nome, valor_mercado: im.valor_mercado, saldo_devedor: im.saldo_devedor,
    taxa_juros_anual: im.taxa_juros_anual, prazo_restante_meses: im.prazo_restante_meses,
    aluguel_receita: im.aluguel_receita,
    custo_financiamento: c.financiamento, custo_condominio: c.condominio, custo_iptu_lixo: c.iptu_lixo,
  };
}

function rowToImovel(r) {
  return {
    nome: r.nome, valor_mercado: r.valor_mercado, saldo_devedor: r.saldo_devedor,
    taxa_juros_anual: r.taxa_juros_anual, prazo_restante_meses: r.prazo_restante_meses,
    aluguel_receita: r.aluguel_receita,
    custos: {
      financiamento: r.custo_financiamento,
      condominio: r.custo_condominio,
      iptu_lixo: r.custo_iptu_lixo,
    },
  };
}

function _addRow(tbody, columns, r) {
  const tr = document.createElement("tr");
  for (const col of columns) {
    const td = document.createElement("td");
    let input;
    if (col.type === "select") {
      input = document.createElement("select");
      for (const o of col.options) {
        const op = document.createElement("option");
        op.value = o; op.textContent = o;
        input.appendChild(op);
      }
      input.value = r[col.key] ?? col.options[0];
    } else {
      input = document.createElement("input");
      input.type = col.type === "number" ? "number" : "text";
      if (col.type === "number") input.step = "0.01";
      input.value = r[col.key] ?? "";
    }
    input.dataset.key = col.key;
    td.appendChild(input);
    tr.appendChild(td);
  }
  const tdDel = document.createElement("td");
  const del = document.createElement("button");
  del.className = "danger"; del.textContent = "✕"; del.title = "Remover";
  del.onclick = () => tr.remove();
  tdDel.appendChild(del);
  tr.appendChild(tdDel);
  tbody.appendChild(tr);
}

function makeTable(containerSel, columns, rows) {
  const c = $(containerSel);
  c.innerHTML = "";
  const table = document.createElement("table");
  table.className = "data-table edit-table";
  table.innerHTML = `<thead><tr>${columns.map((col) => `<th>${col.label}</th>`).join("")}<th></th></tr></thead><tbody></tbody>`;
  c.appendChild(table);
  const tbody = table.querySelector("tbody");
  (rows || []).forEach((r) => _addRow(tbody, columns, r));
  const addBtn = document.createElement("button");
  addBtn.className = "secondary add-row";
  addBtn.textContent = "+ Adicionar linha";
  addBtn.onclick = () => _addRow(tbody, columns, {});
  c.appendChild(addBtn);
}

function readTable(containerSel, columns) {
  const rows = [];
  $(containerSel).querySelectorAll("tbody tr").forEach((tr) => {
    const obj = {};
    let any = false;
    tr.querySelectorAll("[data-key]").forEach((inp) => {
      const col = columns.find((c) => c.key === inp.dataset.key);
      let v = inp.value;
      if (col.type === "number") v = v === "" ? 0 : parseFloat(v);
      if (v !== "" && v !== null && v !== 0) any = true;
      obj[inp.dataset.key] = v;
    });
    if (any) rows.push(obj);
  });
  return rows;
}

async function loadMaintenance() {
  let d;
  try { d = await api("GET", "/api/maintenance"); }
  catch (e) { $("#maint-status").textContent = `Falha: ${e.message}`; return; }
  maintLoaded = true;
  const fp = d.family_profile || {};
  const ov = d.overrides || {};
  maintFullProfile = fp;
  const pat = fp.patrimonio || {};
  makeTable("#maint-receitas", MAINT_COLS.receitas, fp.receitas || []);
  makeTable("#maint-caixa", MAINT_COLS.caixa, pat.investimentos_caixa || []);
  makeTable("#maint-provisoes", MAINT_COLS.provisoes, fp.provisoes || []);
  makeTable("#maint-metas", MAINT_COLS.metas, fp.metas || []);
  makeTable("#maint-imoveis", MAINT_COLS.imoveis, (pat.imoveis || []).map(imovelToRow));
  makeTable("#maint-wishlist", MAINT_COLS.wishlist, fp.wishlist || []);
  const catRows = Object.entries(ov.categorias_pt || {}).map(([en, pt]) => ({ en, pt }));
  makeTable("#maint-categorias", MAINT_COLS.categorias, catRows);
  makeTable("#maint-recorrencias", MAINT_COLS.recorrencias, ov.recorrencias || []);
}

async function saveMaintenance() {
  const status = $("#maint-status");
  status.className = "status";
  const imoveis = readTable("#maint-imoveis", MAINT_COLS.imoveis).map(rowToImovel);

  const fp = { ...maintFullProfile };
  fp.receitas = readTable("#maint-receitas", MAINT_COLS.receitas);
  fp.provisoes = readTable("#maint-provisoes", MAINT_COLS.provisoes);
  fp.metas = readTable("#maint-metas", MAINT_COLS.metas);
  fp.wishlist = readTable("#maint-wishlist", MAINT_COLS.wishlist);
  fp.patrimonio = {
    ...(fp.patrimonio || {}),
    investimentos_caixa: readTable("#maint-caixa", MAINT_COLS.caixa),
    imoveis,
  };

  const categorias_pt = {};
  for (const r of readTable("#maint-categorias", MAINT_COLS.categorias)) {
    if (r.en) categorias_pt[String(r.en).toLowerCase().trim()] = r.pt;
  }
  const recorrencias = readTable("#maint-recorrencias", MAINT_COLS.recorrencias);

  status.textContent = "Salvando…";
  try {
    await api("POST", "/api/maintenance", {
      family_profile: fp,
      overrides: { categorias_pt, recorrencias },
    });
    status.className = "status ok";
    status.textContent = "Salvo! Atualizando dashboard…";
    maintFullProfile = fp;
    await loadDashboard();
  } catch (e) {
    status.className = "status err";
    status.textContent = `Falha: ${e.message}`;
  }
}

$("#btn-maint-save").addEventListener("click", saveMaintenance);
$("#btn-maint-reload").addEventListener("click", () => { maintLoaded = false; loadMaintenance(); });

// ---------------------------------------------------------------- simulador
const SIM_PRESETS = {
  carro: { preco: 80000, entrada: 20000, prazo: 48, juros: 26, rend: 11 },
  imovel: { preco: 300000, entrada: 60000, prazo: 360, juros: 9, rend: 11 },
};

function applyPreset(name) {
  const p = SIM_PRESETS[name];
  if (!p) return;
  $("#sim-preco").value = p.preco;
  $("#sim-entrada").value = p.entrada;
  $("#sim-prazo").value = p.prazo;
  $("#sim-juros").value = p.juros;
  $("#sim-rend").value = p.rend;
}

function num(sel) { return parseFloat($(sel).value) || 0; }

async function simular() {
  const out = $("#sim-result");
  out.innerHTML = `<p class="muted">Calculando…</p>`;
  let r;
  try {
    r = await api("POST", "/api/simular", {
      preco: num("#sim-preco"),
      entrada: num("#sim-entrada"),
      prazo_meses: num("#sim-prazo"),
      juros_aa: num("#sim-juros"),
      sobra_mensal: num("#sim-sobra"),
      rendimento_aa: num("#sim-rend"),
      taxa_adm_consorcio: num("#sim-taxaadm"),
    });
  } catch (e) {
    out.innerHTML = `<p class="bad">Falha: ${e.message}</p>`;
    return;
  }
  const f = r.financiar, j = r.juntar_a_vista, co = r.consorcio;
  const prazoTxt = j.meses_para_juntar
    ? `${j.meses_para_juntar} meses (~${j.anos_para_juntar} anos)`
    : "não atinge (informe a sobra mensal)";
  out.innerHTML = `
    <div class="grid-2" style="margin-top:18px;">
      <div class="card">
        <h3>Financiar</h3>
        <p class="muted small">Valor financiado: ${fmtBRL(r.valor_financiado)} (entrada ${fmtBRL(r.entrada)})</p>
        <table class="data-table">
          <tr><td><strong>Price</strong> — parcela fixa</td><td class="num">${fmtBRL(f.price.parcela)}/mês</td></tr>
          <tr><td>Total pago (Price)</td><td class="num bad">${fmtBRL(f.custo_total_price)}</td></tr>
          <tr><td>Juros (Price)</td><td class="num bad">${fmtBRL(f.price.total_juros)}</td></tr>
          <tr><td><strong>SAC</strong> — 1ª → última</td><td class="num">${fmtBRL(f.sac.primeira_parcela)} → ${fmtBRL(f.sac.ultima_parcela)}</td></tr>
          <tr><td>Total pago (SAC)</td><td class="num bad">${fmtBRL(f.custo_total_sac)}</td></tr>
        </table>
      </div>
      <div class="card">
        <h3>Consórcio</h3>
        <p class="muted small">Sem juros, taxa adm. ${co.taxa_adm_pct}% (uso só após contemplação).</p>
        <table class="data-table">
          <tr><td>Parcela</td><td class="num">${fmtBRL(co.parcela)}/mês</td></tr>
          <tr><td>Total pago</td><td class="num bad">${fmtBRL(co.total_parcelas)}</td></tr>
          <tr><td>Custo da taxa adm.</td><td class="num bad">${fmtBRL(co.custo_taxa_adm)}</td></tr>
        </table>
      </div>
      <div class="card">
        <h3>Juntar à vista</h3>
        <p class="muted small">Guardando ${fmtBRL(j.aporte_mensal)}/mês a ${j.rendimento_aa}% a.a.</p>
        <table class="data-table">
          <tr><td>Tempo para juntar</td><td class="num">${prazoTxt}</td></tr>
          <tr><td>Custo total (à vista)</td><td class="num good">${fmtBRL(j.custo_total)}</td></tr>
          <tr><td>Economia vs financiar (Price)</td><td class="num good">${fmtBRL(r.economia_juntando_vs_price)}</td></tr>
        </table>
      </div>
    </div>`;
}

async function amortizar() {
  const out = $("#amo-result");
  out.innerHTML = `<p class="muted">Calculando…</p>`;
  let r;
  try {
    r = await api("POST", "/api/amortizacao", {
      saldo: num("#amo-saldo"),
      juros_aa: num("#amo-juros"),
      parcela: num("#amo-parcela"),
      aporte_extra: num("#amo-extra"),
    });
  } catch (e) { out.innerHTML = `<p class="bad">Falha: ${e.message}</p>`; return; }
  const sem = r.sem_extra, com = r.com_extra;
  if (!sem) {
    out.innerHTML = `<p class="bad">A parcela não cobre os juros — aumente a parcela.</p>`;
    return;
  }
  out.innerHTML = `
    <table class="data-table" style="margin-top:16px; max-width:560px;">
      <tr><td>Sem aporte extra</td><td class="num">${sem.meses} meses · juros ${fmtBRL(sem.juros_pagos)}</td></tr>
      <tr><td>Com aporte de ${fmtBRL(num("#amo-extra"))}/mês</td><td class="num">${com.meses} meses · juros ${fmtBRL(com.juros_pagos)}</td></tr>
      <tr class="highlight-row"><td>Você economiza</td>
        <td class="num good">${r.meses_economizados} meses · ${fmtBRL(r.juros_economizados)}</td></tr>
    </table>`;
}

async function loadAmortFromImovel() {
  try {
    const m = await api("GET", "/api/maintenance");
    const im = (m.family_profile?.patrimonio?.imoveis || [])[0];
    if (!im) return;
    $("#amo-saldo").value = im.saldo_devedor ?? "";
    $("#amo-juros").value = im.taxa_juros_anual ?? "";
    $("#amo-parcela").value = im.custos?.financiamento ?? "";
  } catch (e) { /* silencioso */ }
}

$$("[data-preset]").forEach((b) => b.addEventListener("click", () => applyPreset(b.dataset.preset)));
$("#btn-simular").addEventListener("click", simular);
$("#btn-amort").addEventListener("click", amortizar);
$("#btn-amort-load").addEventListener("click", loadAmortFromImovel);
$("#dash-period").addEventListener("change", (e) => loadDashboard(e.target.value));

// ---------------------------------------------------------------- boot
$("#btn-connect").addEventListener("click", () => openConnectWidget());
$("#btn-refresh-items").addEventListener("click", refreshItems);
$("#btn-refresh-summary").addEventListener("click", refreshSummary);
$("#btn-sync-all").addEventListener("click", syncAll);

loadDashboard();
refreshSyncStatus();
