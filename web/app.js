// Painel Cartógrafo — vanilla JS, arquitetura por abas.
const api = (rota) => fetch(rota).then((r) => r.json());

// ---- Navegação por abas ----
document.querySelectorAll(".aba").forEach((aba) => {
  aba.addEventListener("click", () => {
    document.querySelectorAll(".aba").forEach((a) => a.classList.remove("ativa"));
    document.querySelectorAll(".painel").forEach((p) => p.classList.remove("ativo"));
    aba.classList.add("ativa");
    const alvo = aba.dataset.aba;
    document.getElementById("painel-" + alvo).classList.add("ativo");
    carregarAba(alvo);
  });
});

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---- Aba Cartas ----
async function carregarCartas() {
  const alvo = document.getElementById("painel-cartas");
  const docs = await api("/api/documentos");
  if (!docs.length) {
    alvo.innerHTML = vazio("Nenhuma carta coletada ainda.", "Clique em \"Coletar agora\" para buscar as mais recentes.");
    return;
  }
  const linhas = docs.map((d) => `
    <tr class="linha-carta" data-id="${d.id}" title="Clique para ver o conteúdo">
      <td class="gestora">${esc(d.gestora)}</td>
      <td>${esc(d.titulo)}</td>
      <td><span class="tag ${esc(d.tipo)}">${esc(d.tipo)}</span></td>
      <td><span class="tag ${esc(d.status)}">${esc(d.status)}</span></td>
      <td>${d.data_publicacao ? d.data_publicacao.slice(0, 10) : "—"}</td>
    </tr>`).join("");
  alvo.innerHTML = `<table>
      <thead><tr><th>Gestora</th><th>Título</th><th>Tipo</th><th>Status</th><th>Data</th></tr></thead>
      <tbody>${linhas}</tbody></table>`;

  alvo.querySelectorAll(".linha-carta").forEach((tr) => {
    tr.addEventListener("click", () => alternarConteudo(tr));
  });
}

// Expande/recolhe o conteúdo da carta logo abaixo da linha clicada.
async function alternarConteudo(tr) {
  const aberta = tr.nextElementSibling?.classList.contains("linha-conteudo");
  if (aberta) { tr.nextElementSibling.remove(); tr.classList.remove("expandida"); return; }
  // fecha qualquer outra aberta
  document.querySelectorAll(".linha-conteudo").forEach((r) => r.remove());
  document.querySelectorAll(".linha-carta.expandida").forEach((r) => r.classList.remove("expandida"));

  tr.classList.add("expandida");
  const detalhe = document.createElement("tr");
  detalhe.className = "linha-conteudo";
  detalhe.innerHTML = `<td colspan="5"><div class="conteudo-carta carregando">carregando…</div></td>`;
  tr.after(detalhe);

  try {
    const d = await api(`/api/documentos/${tr.dataset.id}`);
    const ehPdf = d.tipo === "pdf";
    const visorPdf = `<iframe class="visor-pdf" src="/api/documentos/${d.id}/original#view=FitH"
                        title="${esc(d.titulo)}"></iframe>`;
    const textoExtraido = `<pre class="texto-carta">${esc(d.texto || "(sem texto extraído)")}</pre>`;
    detalhe.innerHTML = `<td colspan="5">
      <div class="conteudo-carta">
        <div class="conteudo-acoes">
          <div class="conteudo-links">
            <a href="${esc(d.url)}" target="_blank" rel="noopener">abrir no site da gestora ↗</a>
            ${ehPdf ? `<button class="btn-alternar" type="button">ver texto extraído</button>` : ""}
          </div>
          <span class="conteudo-meta">${esc(d.tipo)} · ${(d.texto || "").length.toLocaleString("pt-BR")} caracteres extraídos</span>
        </div>
        <div class="corpo-visor">${ehPdf ? visorPdf : textoExtraido}</div>
      </div></td>`;

    // PDF: alterna entre o documento original (tabelas/gráficos) e o texto puro.
    const btn = detalhe.querySelector(".btn-alternar");
    if (btn) {
      const corpo = detalhe.querySelector(".corpo-visor");
      let mostrandoPdf = true;
      btn.addEventListener("click", () => {
        mostrandoPdf = !mostrandoPdf;
        corpo.innerHTML = mostrandoPdf ? visorPdf : textoExtraido;
        btn.textContent = mostrandoPdf ? "ver texto extraído" : "ver documento original";
      });
    }
  } catch {
    detalhe.innerHTML = `<td colspan="5"><div class="conteudo-carta">falha ao carregar o conteúdo</div></td>`;
  }
}

// ---- Aba Resumos ----
async function carregarResumos() {
  const alvo = document.getElementById("painel-resumos");
  const resumos = await api("/api/resumos");
  if (!resumos.length) {
    alvo.innerHTML = vazio("Nenhum resumo disponível.", "Os resumos aparecem aqui após o pipeline de IA ser acoplado e executado.");
    return;
  }
  alvo.innerHTML = resumos.map((r) => {
    const c = r.completo || {};
    const juros = r.visao_juros?.vies ? `Juros: <b>${esc(r.visao_juros.vies)}</b>` : "";
    const infla = r.visao_inflacao?.vies ? `Inflação: <b>${esc(r.visao_inflacao.vies)}</b>` : "";
    const badges = [juros, infla].filter(Boolean)
      .map((b) => `<span class="badge">${b}</span>`).join("");
    const posicoes = (r.posicoes_direcionais || []).map((p) => {
      const dir = (p.direcao || "neutro").includes("long") ? "long"
        : (p.direcao || "").includes("short") ? "short" : "neutro";
      return `<span class="chip ${dir}">${esc(p.ativo_ou_classe)} · ${esc(p.direcao)}</span>`;
    }).join("");
    const setores = (r.teses_setoriais || [])
      .map((t) => `<span class="chip neutro">${esc(t.setor_ou_acao)}: ${esc(t.direcao)}</span>`).join("");
    return `<article class="card">
      <h3>${esc(c.gestora || "Gestora")}${c.periodo_referencia ? " · " + esc(c.periodo_referencia) : ""}</h3>
      <p class="tese">${esc(c.tese_principal || "")}</p>
      ${badges ? `<div class="linha-badges">${badges}</div>` : ""}
      ${posicoes ? `<div class="rotulo">Posições direcionais</div><div class="chips">${posicoes}</div>` : ""}
      ${setores ? `<div class="rotulo">Teses setoriais</div><div class="chips">${setores}</div>` : ""}
    </article>`;
  }).join("");
}

// ---- Aba Consenso ----
async function carregarConsenso() {
  const alvo = document.getElementById("painel-consenso");
  const c = await api("/api/consenso");
  if (!c.consensos?.length && !c.divergencias?.length && !c.leitura_macro) {
    alvo.innerHTML = vazio("Relatório de consenso não gerado.", "Disponível após os resumos serem cruzados pelo motor de consenso.");
    return;
  }
  const consensos = (c.consensos || []).map((x) => `
    <div class="item-consenso">
      <span class="tema">${esc(x.tema)}</span>
      <span class="forca">${esc(x.forca)} · ${esc(x.percentual || "")}</span>
      <div>Lado: <b>${esc(x.lado)}</b></div>
      ${x.observacao ? `<div style="color:var(--muted)">${esc(x.observacao)}</div>` : ""}
      <div class="gestoras-chips">${(x.gestoras || []).map((g) => `<span class="gchip">${esc(g)}</span>`).join("")}</div>
    </div>`).join("");
  const divergencias = (c.divergencias || []).map((x) => `
    <div class="item-consenso">
      <div class="tema">${esc(x.tema)}</div>
      <div class="divergencia" style="margin-top:8px">
        <div class="lado a"><b>${esc(x.lado_a?.posicao || "")}</b>
          <div class="gestoras-chips">${(x.lado_a?.gestoras || []).map((g) => `<span class="gchip">${esc(g)}</span>`).join("")}</div></div>
        <div class="versus">vs</div>
        <div class="lado b"><b>${esc(x.lado_b?.posicao || "")}</b>
          <div class="gestoras-chips">${(x.lado_b?.gestoras || []).map((g) => `<span class="gchip">${esc(g)}</span>`).join("")}</div></div>
      </div>
      ${x.observacao ? `<div style="color:var(--muted);margin-top:8px">${esc(x.observacao)}</div>` : ""}
    </div>`).join("");
  const macro = c.leitura_macro
    ? `<div class="bloco-consenso leitura-macro"><h2>Leitura macro</h2><p>${esc(c.leitura_macro)}</p></div>`
    : "";
  alvo.innerHTML = `
    ${macro}
    <div class="bloco-consenso"><h2>Consenso de mercado · ${esc(c.periodo || "")}</h2>${consensos || vazioInline("Sem consensos.")}</div>
    <div class="bloco-consenso"><h2>Divergências</h2>${divergencias || vazioInline("Sem divergências.")}</div>`;
}

// ---- Aba Fontes (status de coleta por gestora) ----
async function carregarFontes() {
  const alvo = document.getElementById("painel-fontes");
  const fontes = await api("/api/status-fontes");
  if (!fontes.length) {
    alvo.innerHTML = vazio("Nenhuma coleta registrada ainda.", "Clique em \"Coletar agora\" para tentar todas as fontes.");
    return;
  }
  const linhas = fontes.map((f) => `
    <tr>
      <td class="gestora">${esc(f.gestora)}</td>
      <td><span class="tag ${f.sucesso ? "ok" : "erro"}">${f.sucesso ? "ok" : "falha"}</span></td>
      <td class="motivo">${esc(f.motivo || "—")}</td>
      <td>${f.em ? f.em.slice(0, 16).replace("T", " ") : "—"}</td>
    </tr>`).join("");
  alvo.innerHTML = `<table>
      <thead><tr><th>Gestora</th><th>Resultado</th><th>Motivo</th><th>Última tentativa</th></tr></thead>
      <tbody>${linhas}</tbody></table>`;
}

const vazio = (titulo, dica) => `<div class="vazio"><strong>${esc(titulo)}</strong><br>${esc(dica)}</div>`;
const vazioInline = (t) => `<div class="vazio" style="padding:20px">${esc(t)}</div>`;

function carregarAba(nome) {
  if (nome === "cartas") carregarCartas();
  else if (nome === "resumos") carregarResumos();
  else if (nome === "consenso") carregarConsenso();
  else if (nome === "fontes") carregarFontes();
}

// ---- Botão coletar (coleta assíncrona com polling de status) ----
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function aguardarColeta(status) {
  while (true) {
    await sleep(2000);
    const st = await api("/api/coletar/status");
    if (st.rodando) continue;
    if (st.erro) { status.textContent = "falha na coleta"; return; }
    const r = st.resultado;
    status.textContent = r
      ? `${r.novos} novas · ${r.duplicados} repetidas · ${r.falhas} falhas (de ${r.total})`
      : "coleta concluída";
    carregarCartas();
    carregarFontes();
    return;
  }
}

document.getElementById("btn-coletar").addEventListener("click", async (e) => {
  const btn = e.target;
  const status = document.getElementById("status-coleta");
  btn.disabled = true; status.textContent = "coletando…";
  try {
    const res = await fetch("/api/coletar", { method: "POST" });
    if (res.status === 409) { status.textContent = "coleta já em andamento"; return; }
    await aguardarColeta(status);
  } catch (err) {
    status.textContent = "falha na coleta";
  } finally {
    btn.disabled = false;
    setTimeout(() => (status.textContent = ""), 6000);
  }
});

// inicial
carregarCartas();
