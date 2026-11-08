# Publicação da API (Render)

O Priora em produção usa:

| Parte | Onde | Repositório |
|---|---|---|
| API (este repositório) | **Render** (plano Free, Docker) | `priora-server` |
| Front | **Vercel** | `priora-client` (veja o `DEPLOY.md` de lá) |
| Banco | Neo4j Aura | — |
| Imagens | Supabase Storage | — |

> Publique **primeiro a API**, depois o front, e por fim volte aqui para preencher o endereço do front (passo 4).

## 0. Antes de publicar

- [ ] **Troque as credenciais que já circularam fora do `.env`** (senha do Neo4j no console do Aura, senha de app do Gmail, chave `service_role` do Supabase).
- [ ] **Buckets no Supabase:** confira que existem `quadro-investigativo`, `suspect-photos` e `user-photos`.
- [ ] **Região do Aura:** veja no console do Aura e ajuste `region` no [`render.yaml`](render.yaml) para a mais próxima (padrão: `ohio`).
- [ ] **Branch:** o `render.yaml` publica a `dev`. Para publicar outra, mude `branch`.

## 1. Criar o serviço pelo Blueprint

1. Entre em [render.com](https://render.com) com a conta do GitHub.
2. **New → Blueprint** e escolha o repositório `priora-server`.
3. O Render lê o [`render.yaml`](render.yaml) e pede os valores marcados como secretos:

| Variável | Valor |
|---|---|
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_DATABASE` | os do Aura |
| `NEO4J_PASSWORD` | a **nova** senha do Aura |
| `MAIL_USERNAME`, `MAIL_FROM`, `SUPPORT_EMAIL` | e-mail de suporte do Priora |
| `MAIL_PASSWORD` | a **nova** senha de app do Gmail |
| `SUPABASE_URL` | URL do projeto no Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | a **nova** chave `service_role` |
| `PUBLIC_API_URL` | o endereço desta API, ex.: `https://priora-api.onrender.com` (se ainda não souber, preencha depois) |
| `FRONTEND_URL`, `CORS_ORIGINS` | por enquanto qualquer valor; corrigidos no passo 4 |

O `SECRET_KEY` é **gerado pelo Render** (aleatório). `PORT`, `ALGORITHM`, `MAIL_SERVER`, `MAIL_PORT` e os nomes dos buckets já vêm preenchidos.

4. Clique em **Apply**. Ao terminar, abra o endereço da API: deve responder `{"message": "Priora backend is running 🚀"}`. A documentação interativa fica em `/docs`.

## 2. Publicar o front

Siga o `DEPLOY.md` do `priora-client`, usando o endereço desta API em `VITE_API_URL`.

## 3. Conferir o `PUBLIC_API_URL`

Em **Environment**, confira se `PUBLIC_API_URL` é o endereço real da API (sem barra no final).

## 4. Ligar a API ao front

Em **Environment**, troque pelo endereço do Vercel (sem barra no final):

- `FRONTEND_URL` → usado no link do e-mail de recuperação de senha
- `CORS_ORIGINS` → sem isso o navegador bloqueia as chamadas do front

Salvar dispara um novo deploy.

## 5. Testar

- [ ] Cadastro e login
- [ ] Criar caso, suspeito e evidência
- [ ] Foto de perfil e imagem no quadro investigativo (Supabase)
- [ ] Recuperação de senha: o e-mail chega e o link abre o site do Vercel

## Plano Free: o que esperar

- **A API "dorme"** após ~15 min sem acesso; a 1ª requisição depois disso leva **30–60 s**. Em apresentações, abra o site alguns minutos antes.
- **Disco temporário:** apagado a cada deploy. Por isso o Supabase é obrigatório em produção.
- **Neo4j Aura Free** pausa a instância após dias sem uso. Se a API falhar ao conectar, retome a instância no console do Aura.
- **Cada push na branch publicada** gera um novo deploy automaticamente.

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| Deploy falha com erro do Neo4j | `NEO4J_*` errado ou instância do Aura pausada |
| Front mostra erro de CORS | `CORS_ORIGINS` diferente do endereço exato do Vercel |
| E-mail de recuperação não chega | O plano pode bloquear SMTP; nesse caso, troque o envio por um serviço de e-mail com API (ex.: Resend, Brevo) |
| Imagens somem depois de um deploy | `SUPABASE_*` vazio: as imagens foram para o disco temporário |
| Todos foram deslogados | `SECRET_KEY` mudou (os tokens antigos deixam de valer) |
