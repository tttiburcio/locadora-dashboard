# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Financial dashboard for a vehicle rental fleet (*locadora*). Reads `Locadora.xlsx` and exposes a React + FastAPI web application. The original Streamlit version (`app.py`) is kept for reference but is no longer the primary interface.

## Running the Project

**One-shot (Windows):**
```
start.bat
```
Opens both servers and launches the browser automatically.

**Manually (two terminals):**
```bash
# Backend — porta 8000
cd backend
python -m uvicorn main:app --reload --port 8000

# Frontend — porta 5173
cd frontend
npm run dev
```

**Build de produção do frontend:**
```bash
cd frontend && npm run build   # output em frontend/dist/
```

## Architecture

```
Locadora.xlsx  ←── única fonte de dados (lida pelo pandas via openpyxl)
     │
     ▼
backend/main.py  (FastAPI)          porta 8000
     │  endpoints: /api/years, /api/kpis, /api/monthly,
     │             /api/vehicles, /api/vehicle/{placa}
     │  query param obrigatório: ?year=<int>
     ▼
frontend/src/   (React 18 + Vite)   porta 5173
     │  proxy /api → localhost:8000  (vite.config.js)
     │
     ├─ App.jsx            estado global (year, page, kpis, monthly, vehicles)
     ├─ pages/
     │    OverviewPage.jsx   KPIs + gráficos de frota
     │    VehiclesPage.jsx   tabela filtrável/ordenável de todos os veículos
     ├─ components/
     │    Sidebar.jsx        navegação + seletor de ano + legenda de cores
     │    KPICard.jsx        card reutilizável com ícone/valor/trend
     │    VehicleModal.jsx   drawer lateral com análise completa de 1 veículo
     │    charts/
     │      MonthlyChart.jsx      evolução mensal (receita e custos)
     │      FleetCharts.jsx       pizza saúde da frota, pizza custos, top veículos
     │      VehicleCharts.jsx     gráfico mensal + pizza de custos por veículo
     └─ utils/
          api.js     chamadas axios para o backend
          format.js  brl(), brlShort(), pct(), dias(), num()
```

## Data Pipeline (backend/main.py)

A função `compute(year)` é o núcleo:

1. Lê todas as abas do Excel via `load_raw()` (cached em `_cache` dict em memória)
2. Filtra cada DataFrame pelo ano selecionado usando a coluna de data apropriada
3. **Deduplicação de manutenção**: `manutencoes` repete `TotalOS` por categoria/parcela da mesma OS — remove duplicatas por `IDOrdServ` (mantém `com_os` sem duplicatas + `sem_os` separadamente)
4. Agrega receitas e custos por `IDVeiculo` e faz join com `frota` (left join — preserva veículos sem movimento)
5. Retorna: `(df_active, monthly, kpis, fat, reimb, manut, seg, rast, imp)` — os DataFrames filtrados são passados adiante para o endpoint `/api/vehicle/{placa}` reutilizar sem reprocessar

## Excel Sheets & Key Columns

| Chave interna | Nome da aba | Colunas críticas |
|---|---|---|
| `frota` | 🚛 FROTA | `IDVeiculo`, `Placa`, `Marca`, `Modelo`, `Status`, `ValorTotal` |
| `fat_unitario` | 💰 FAT_UNITARIO | `Mes` (date), `IDVeiculo`, `Medicao` (receita), `Trabalhado`, `Parado` |
| `reembolsos` | ↩️ REEMBOLSOS | `Emissão` (date), `IDVeiculo`, `ValorReembolso` |
| `manutencoes` | 🔧 MANUTENCOES | `DataExecução` (date), `IDVeiculo`, `IDOrdServ`, `TotalOS` |
| `faturamento` | 🧾 FATURAMENTO | `Emissão` (date), `ValorLocacoes`, `ValorRecebido` |
| `seguro_mensal` | 📋 SEGURO_MENSAL | `Vencimento` (date), `IDVeiculo`, `Valor` |
| `impostos` | 📋 IMPOSTOS | `AnoImposto` (int), `IDVeiculo`, `ValorTotalFinal` |
| `rastreamento` | 📍RASTREAMENTO | `Vencimento` (date), `IDVeiculo`, `Valor` |

> `impostos` filtra por `AnoImposto == year` (inteiro), não por data. As demais filtram por `.dt.year`.
> O nome da aba `rastreamento` **não tem espaço** após o emoji: `"📍RASTREAMENTO"`.

## Color System (Tailwind)

Escala customizada `g-*` (verde escuro) definida em `tailwind.config.js`:
- Backgrounds: `bg-g-950` (#031a0e) → `bg-g-850` (#083a1e) → `bg-g-800` (#0f4a27)
- Texto: `text-g-50` (claro) → `text-g-400` (atenuado) → `text-g-600` (muted)
- Cores fixas por categoria nos gráficos: locação `#22c55e`, reembolso `#34d399`, manutenção `#f97316`, seguro `#ef4444`, impostos `#a855f7`, rastreamento `#f59e0b`

## Deployment

O repositório remoto é `https://github.com/tttiburcio/locadora-dashboard.git` (branch `master` → `main`).  
**Deploy automático:** ao concluir qualquer tarefa, fazer commit + push para o GitHub sem aguardar confirmação do usuário.
