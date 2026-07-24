# Cartógrafo — Cartas de Gestores

Pipeline modular para **extração, armazenamento e sumarização** de cartas de
gestores e relatórios macroeconômicos das principais assets brasileiras.
Coleta as cartas mais recentes de cada fonte (até `max_documentos` por gestora
— cobrindo casas com uma carta por fundo/série, como Kapitalo e Occam),
persiste em SQLite, gera um resumo técnico estruturado por carta e um relatório
de **consenso × divergência** de mercado.

> Persistência: **SQLite apenas**. O pipeline de IA é um **contrato plugável** —
> o modelo real é interno do banco e acoplado depois, sem refatorar o restante.

## Arquitetura

```
Fontes (30 gestoras)
        │  registry declarativo
        ▼
Orquestrador (APScheduler)
        │
   ┌────┴─────┐
httpx       Playwright          (estático / dinâmico)
   └────┬─────┘
BeautifulSoup   pdfplumber+OCR   (HTML / PDF)
        │
Normalização + dedup (SHA-256)
        │
   Armazenamento (SQLite)
        │
Pipeline LLM (resumo individual)   ← contrato plugável (modelo do banco)
        │
Motor de consenso (market summary)
        │
   API REST (FastAPI) + painel vanilla JS
```

## Estrutura

```
cartografo/
├── config.py            # settings (env vars)
├── registry.py          # FonteConfig + REGISTRY das 21 fontes
├── schemas.py           # DocumentoColetado (contrato de coleta)
├── fetch/               # http (httpx) + dynamic (Playwright)
├── extract/             # html (BeautifulSoup) + pdf (pdfplumber/OCR)
├── scrapers/            # base + dynamo (PDF) + kinea (HTML) + factory
├── db/                  # models (ORM) + repository (SQLite)
├── ai/                  # client (interface), prompts, resumo, consenso
├── pipeline.py          # orquestração coleta→resumo→consenso
├── scheduler.py         # APScheduler
├── api/app.py           # FastAPI + serve o painel
└── run.py               # CLI
web/                     # painel vanilla JS (abas: Cartas, Resumos, Consenso, Fontes)
```

## Instalação

```bash
python -m venv .venv && source .venv/bin/activate
pip install .                 # núcleo (equivale a requirements.txt)
# extras opcionais, sob demanda:
pip install ".[dynamic]"      # Playwright (fontes SPA/JS) → playwright install chromium
pip install ".[ocr]"          # OCR de PDFs escaneados (PyMuPDF + tesseract)
pip install ".[dev]"          # pytest + ruff
cp .env.example .env
```

## Testes

```bash
pip install ".[dev]"
pytest
```

Cobrem as partes determinísticas (dedup por hash, descoberta heurística,
pré-agregação de consenso, extração de corpo/data, truncamento ao LLM) — sem rede.

## Uso (CLI)

```bash
python -m cartografo.run coletar     # coleta todas as fontes ativas
python -m cartografo.run coletar --fontes dynamo kinea   # só fontes específicas
python -m cartografo.run resumir     # gera resumos (requer IA acoplada)
python -m cartografo.run consenso    # gera o relatório de consenso
python -m cartografo.run ciclo       # coleta + resumo + consenso
python -m cartografo.run api         # sobe API + painel em http://127.0.0.1:8000
python -m cartografo.run scheduler   # agendamento automático
```

## Acoplar o modelo de IA do banco

Implemente o contrato `LLMClient` (`cartografo/ai/client.py`):

```python
from cartografo.ai.client import LLMClient

class ModeloInternoBanco(LLMClient):
    def __init__(self, endpoint, token):
        self.endpoint, self.token = endpoint, token

    def resumir(self, system_prompt: str, user_content: str) -> str:
        # POST no endpoint interno; retornar a STRING JSON do modelo
        ...
        return resposta_em_json
```

O retorno deve ser **apenas o JSON** no schema de `SYSTEM_PROMPT_RESUMO`
(`cartografo/ai/prompts.py`). Passe a instância para `executar_resumos(llm)` /
`executar_consenso(llm=...)`. Nada mais no código muda.

## Adicionar uma nova gestora

1. Adicione uma `FonteConfig` em `cartografo/registry.py` (já há 30 catalogadas).
   - `max_documentos` controla quantas cartas por execução;
   - `paginas_extra` aceita listagens adicionais (ex.: uma página por fundo,
     como as 5 séries da Kapitalo — Kappa/Zeta, NW3, K10, Tarkus, Temáticas);
   - `urls_diretas` baixa documentos de URL fixa sem etapa de descoberta
     (ex.: os relatórios mensais por fundo da Ibiuna, cujo PDF mantém a mesma
     URL e troca de conteúdo a cada edição — o dedup por hash detecta).
2. (Opcional) Crie um scraper concreto em `cartografo/scrapers/` herdando de
   `BaseScraper` — implemente `coletar()` para múltiplas cartas — e registre-o
   em `cartografo/scrapers/factory.py`. Sem scraper dedicado, vale o genérico.

## Robustez e fallbacks

Todas as 30 fontes são tentadas a cada coleta. Quem não tem scraper dedicado
(Dynamo, Kinea, Genoa) cai no **scraper genérico**, guiado por heurística, que
coleta até `max_documentos` cartas por fonte (deduplicadas por URL e por hash
de conteúdo). Cada etapa tem cascata de fallbacks:

- **Rede**: retry com backoff exponencial + rotação de User-Agent; se um agente
  é bloqueado, tenta o próximo.
- **Renderização**: fontes estáticas tentam `httpx` e escalam para Playwright se
  o conteúdo vier curto; fontes dinâmicas tentam Playwright e caem para estático.
- **Descoberta do documento**: usa o seletor configurado e, na ausência dele,
  pontua todos os links por palavras-chave (carta, relatório, gestor, mês, ano)
  e extensão `.pdf` para achar a publicação mais recente.
- **Tipo de arquivo**: detectado por *magic bytes* (`%PDF`), não só pela extensão.
- **Extração de PDF**: `pdfplumber` → `PyMuPDF` → **OCR** (tesseract) para
  documentos escaneados.
- **Isolamento por fonte**: uma exceção numa gestora nunca derruba o lote. Cada
  tentativa é gravada em `logs_coleta` (sucesso/falha + motivo), visível em
  `GET /api/status-fontes` e na aba **Fontes** do painel.

A coleta retorna um resumo agregado: `{total, novos, duplicados, falhas, detalhes}`.

### Coleta via API (assíncrona)

`POST /api/coletar` dispara a coleta em **background** (pode levar minutos) e
responde `202` imediatamente; um novo disparo enquanto outra coleta roda recebe
`409`. Acompanhe o andamento em `GET /api/coletar/status`
(`{rodando, iniciada_em, concluida_em, resultado, erro}`). O painel já faz esse
polling ao clicar em **Coletar agora**.

## Notas de operação

- Respeite `robots.txt` e os termos de uso de cada gestora. Várias fontes
  (SPX, BTG, XP Asset, Vinci) exigem cadastro/login e têm proteção anti-bot;
  há `CARTOGRAFO_DELAY` para espaçar requisições.
- `PRAGMA journal_mode=WAL` está ativo: a API lê enquanto o coletor escreve.
- Os seletores CSS das fontes ficam no `registry.py` para ajuste sem refatoração.
