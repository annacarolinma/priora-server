# Publicação da API (Azure)

O Priora em produção usa:

| Parte | Onde | Repositório |
|---|---|---|
| API (este repositório) | **Azure App Service** (Linux, Python, plano B1) | `priora-server` |
| Front | **Vercel** | `priora-client` (veja o `DEPLOY.md` de lá) |
| Banco | Neo4j Aura | — |
| Imagens | Supabase Storage | — |

> Publique **primeiro a API**, depois o front, e por fim volte aqui para preencher o endereço do front (passo 6).

A API roda direto do código Python (sem Docker): a Azure instala o `requirements.txt` a cada deploy e sobe o `uvicorn`. O `Dockerfile` continua servindo para rodar localmente.

## 0. Antes de publicar

- [ ] **Azure for Students** ativado (azure.microsoft.com/free/students, com o e-mail da faculdade).
- [ ] **Troque as credenciais que já circularam fora do `.env`**: senha do Neo4j (console do Aura), senha de app do Gmail e chave `service_role` do Supabase.
- [ ] **Buckets no Supabase:** confira que existem `quadro-investigativo`, `suspect-photos` e `user-photos`.
- [ ] **Região do Aura:** anote no console do Aura (ex.: us-east). A API deve ficar na mesma região ou perto.
- [ ] **Acesso ao GitHub:** para ligar o deploy (passo 4), quem configura precisa ser admin do repositório, ou o dono precisa autorizar o app da Azure no GitHub.

## 1. Controle de gastos

Em **Cost Management → Budgets**, crie um orçamento (ex.: US$ 20/mês) com aviso por e-mail.

O plano B1 custa em torno de US$ 13/mês, pago com o crédito de estudante. Se o crédito acabar ou vencer, a Azure **desliga** os serviços (não cobra cartão).

## 2. Criar o Web App

1. Crie um **Resource group** (ex.: `priora-rg`).
2. **Create → Web App**:

| Campo | Valor |
|---|---|
| Publish | **Code** |
| Runtime stack | **Python 3.13** |
| Operating System | **Linux** |
| Region | a mais perto do Aura (ex.: East US) |
| Pricing plan | **Basic B1** (não use o F1: ele "dorme" e tem limite de CPU por dia) |
| Name | ex.: `priora-api` → endereço `https://priora-api.azurewebsites.net` (a Azure pode acrescentar um sufixo) |

## 3. Configurar

### Settings → Configuration

| Opção | Valor |
|---|---|
| **Always On** | ligado (é o que impede a API de "dormir") |
| **HTTPS Only** | ligado |
| **Startup Command** | `uvicorn main:app --host 0.0.0.0 --port 8000` |

### Settings → Environment variables

| Variável | Valor |
|---|---|
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_DATABASE` | os do Aura |
| `NEO4J_PASSWORD` | a **nova** senha do Aura |
| `SECRET_KEY` | chave nova e forte: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ALGORITHM` | `HS256` |
| `JWT_EXPIRE_HOURS` | `12` |
| `MAIL_SERVER` | `smtp.gmail.com` |
| `MAIL_PORT` | `587` |
| `MAIL_USERNAME`, `MAIL_FROM`, `SUPPORT_EMAIL` | e-mail de suporte do Priora |
| `MAIL_PASSWORD` | a **nova** senha de app do Gmail |
| `SUPABASE_URL` | URL do projeto no Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | a **nova** chave `service_role` |
| `PUBLIC_API_URL` | o endereço do Web App, sem barra no final |
| `FRONTEND_URL`, `CORS_ORIGINS` | por enquanto `http://localhost:5173`; corrigidos no passo 6 |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` (faz a Azure rodar o `pip install` no deploy) |

Os nomes dos buckets já têm padrão no código; só defina `SUPABASE_*_BUCKET` se usar outros nomes.

Nunca coloque esses valores no repositório.

## 4. Deploy automático (GitHub Actions)

1. **Deployment Center → Source: GitHub**, escolha o repositório `priora-server` e a branch **`dev`**.
2. Em autenticação, prefira **User-assigned identity** (não precisa de senha guardada no GitHub).
3. Salve. A Azure faz um commit na `dev` com o workflow em `.github/workflows/`; dê `git pull` depois.
4. Acompanhe o primeiro deploy na aba **Actions** do GitHub.

Daí em diante, **cada push na `dev` publica a API sozinho**.

## 5. Testar a API

- Abra o endereço do Web App: deve responder `{"message": "Priora backend is running 🚀"}`.
- A documentação interativa fica em `/docs`.
- Se der erro, veja **Monitoring → Log stream** no portal.

## 6. Ligar a API ao front

Depois de publicar o front (`DEPLOY.md` do `priora-client`, com `VITE_API_URL` = endereço desta API), volte em **Environment variables** e troque pelo endereço do Vercel (sem barra no final):

- `FRONTEND_URL` → usado no link do e-mail de recuperação de senha
- `CORS_ORIGINS` → sem isso o navegador bloqueia as chamadas do front (vários endereços separados por vírgula)

Salvar reinicia a API.

## 7. Testar tudo

- [ ] Cadastro e login
- [ ] Criar caso, suspeito e evidência
- [ ] Foto de perfil e imagem no quadro investigativo (Supabase)
- [ ] Recuperação de senha: o e-mail chega e o link abre o site do Vercel

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| "Application Error" ao abrir a API | Veja o Log stream. Em geral: variável faltando (ex.: `MAIL_PORT`), `NEO4J_*` errado ou instância do Aura pausada |
| `ModuleNotFoundError` no log | `SCM_DO_BUILD_DURING_DEPLOYMENT` ausente: o `pip install` não rodou |
| A 1ª requisição demora | **Always On** desligado, ou plano F1 |
| Front mostra erro de CORS | `CORS_ORIGINS` diferente do endereço exato do Vercel |
| E-mail de recuperação não chega | Senha de app do Gmail errada, ou `MAIL_*` incompleto |
| Todos foram deslogados | `SECRET_KEY` mudou (os tokens antigos deixam de valer) |
| A API parou do nada | Crédito de estudante acabou ou venceu; veja em **Cost Management** |

**Neo4j Aura Free** pausa a instância após dias sem uso: se a API falhar ao conectar, retome a instância no console do Aura.
