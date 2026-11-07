# 🧠 Priora — Backend

Backend do sistema **Probabilistic Investigative Prioritization System (Priora)**.

Este serviço é responsável pelo processamento das evidências, cálculo probabilístico e gerenciamento dos dados investigativos.

---

## ⚡ Quick Start

### Opção 1 — Docker (recomendada: tudo local, nenhum dado sai da máquina)

```bash
cp .env.example .env      # preencha SECRET_KEY, MAIL_* e SUPPORT_EMAIL
docker compose up -d --build
```

* API: http://localhost:8000 (docs em `/docs`)
* Neo4j Browser: http://localhost:7474 (usuário `neo4j`, senha = `NEO4J_LOCAL_PASSWORD`)
* O banco fica no volume `neo4j_data` e as imagens do quadro em `uploads`.
  Deixe `SUPABASE_*` vazio no `.env` para não depender de nuvem.
* Para apagar todos os dados: `docker compose down -v`.
* O front roda à parte (`npm run dev` no `priora_client`, porta 5173).

### Opção 2 — Python local (usa o Neo4j do `.env`, ex.: Aura)

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 🚀 Tecnologias

* Python
* FastAPI
* Neo4j
* pgmpy
* NetworkX
* Docker

---

## 📁 Estrutura do Projeto

```
app/
├── api/        # Rotas da API
├── services/   # Regras de negócio
├── models/     # Modelos de dados
├── bayes/      # Inferência probabilística
├── graph/      # Modelagem de relações
└── database/   # Conexão com banco
```

---

## ⚙️ Setup do Projeto

### 🔹 1. Clonar repositório

```bash
git clone <repo-url>
cd investigative-system-server
```

---

### 🔹 2. Criar e ativar ambiente virtual

```bash
python -m venv venv
```

#### Windows:

```bash
venv\Scripts\activate
```

#### Linux/Mac:

```bash
source venv/bin/activate
```

---

### 🔹 3. Instalar dependências

```bash
pip install -r requirements.txt
```

---

### 🔹 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test123
```

---

## 🐳 Banco de Dados (Neo4j)


### ▶️ Rodar o servidor

```bash
uvicorn main:app --reload
```

Acesse:

http://localhost:8000
http://localhost:8000/docs

---

### ⚠️ Importante

* Sempre ative o ambiente virtual antes de rodar o projeto

---

## 🧪 Desenvolvimento

Para adicionar novas funcionalidades:

* Rotas → `app/api`
* Regras → `app/services`
* Modelos → `app/models`

---

## 📌 Objetivo

Este backend tem como objetivo fornecer uma base estruturada para:

* Processamento de evidências
* Inferência probabilística
* Priorização de suspeitos
* Análise de relações investigativas
