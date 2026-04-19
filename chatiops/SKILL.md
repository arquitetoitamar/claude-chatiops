---
name: chatiops
description: >
  Integra o Claude com o WhatsApp através da API REST oficial da plataforma Chatiops
  (https://api.chatiops.tiops.com.br). Use esta skill SEMPRE que o usuário pedir para
  enviar mensagem no WhatsApp, "mandar um zap", disparar WhatsApp, enviar PDF/imagem/
  áudio/vídeo pelo WhatsApp, configurar webhook de WhatsApp, receber mensagens do
  WhatsApp, fechar ticket no Chatiops, notificar cliente via WhatsApp, mandar OTP, ou
  qualquer operação envolvendo a plataforma Chatiops. Gatilhos em português comuns:
  "manda zap", "envia whats pro fulano", "dispara um whatsapp", "avisa no zap",
  "manda uma mensagem pro cliente", "confirmação por whatsapp", "lembrete no zap",
  "mandar boleto no whatsapp". Dispare esta skill mesmo quando o usuário não mencionar
  "Chatiops" explicitamente — se o pedido envolve enviar qualquer mensagem via
  WhatsApp de forma programática, é esta skill.
---

# Chatiops — Envio de WhatsApp via API

Esta skill integra o Claude com a **API REST do Chatiops**, uma plataforma brasileira
de atendimento e envio programático via WhatsApp. A API é bem simples: um único
endpoint de envio que aceita texto ou mídia, autenticação por token Bearer, e um
webhook para receber mensagens.

## Configuração base

```
BASE_URL: https://api.chatiops.tiops.com.br
AUTH:     Authorization: Bearer <TOKEN>
```

Cada token é **vinculado a uma conexão WhatsApp específica** dentro do Chatiops.
O usuário gera o token no painel (Conexões → escolher a conexão → aba API → "Gerar
Token"). Tokens não expiram; para revogar basta gerar outro, que invalida o anterior.

> Se o usuário ainda não passou o token, peça educadamente. Evite pedir o token no
> primeiro turno se a conversa é exploratória ("como funciona?") — só peça quando ele
> quiser de fato disparar uma mensagem. O token é sensível: nunca peça para ele colar
> o token em arquivos versionados. Prefira guardar em variável de ambiente
> `CHATIOPS_TOKEN`.

## Formato do número

Sempre no padrão internacional, **sem sinal de `+`, sem espaços, sem traços**:

| País    | DDD | Número        | Resultado           |
|---------|-----|---------------|---------------------|
| Brasil  | 11  | 99999-9999    | `5511999999999`     |
| Brasil  | 12  | 99151-2954    | `5512991512954`     |
| Portugal| —   | 912 345 678   | `351912345678`      |

Se o usuário passar o número "cru" (ex: `(11) 99999-9999`), normalize automaticamente
antes de enviar. Confirme com ele o país quando o número começar sem código (ex:
`11999999999` sem `55` na frente).

## Endpoint único: envio de mensagem

Todo o envio (texto OU mídia) usa o mesmo endpoint: `POST /api/messages/send`.
O que muda é o `Content-Type`:

- **Texto puro** → `application/json`
- **Com arquivo** (PDF, imagem, áudio, vídeo) → `multipart/form-data`

Para detalhes completos de cada caso, exemplos de `curl`, payloads de webhook e
códigos de erro, consulte: `references/api.md`.

### Campos do body

| Campo         | Tipo    | Obrig. | Descrição                                                |
|---------------|---------|--------|----------------------------------------------------------|
| `number`      | string  | sim    | Número destino, formato `5511999999999`                  |
| `body`        | string  | sim    | Texto da mensagem (legenda, quando há mídia)             |
| `priority`    | string  | não    | `baixa` (padrão), `media`, `alta`                        |
| `closeTicket` | boolean | não    | Se `true`, fecha o ticket após o envio                   |
| `medias`      | file    | não    | Arquivo anexo (só em `multipart/form-data`)              |

### O campo `priority` — cuidado importante

| Valor   | Delay     | Quando usar                                       |
|---------|-----------|---------------------------------------------------|
| `baixa` | 1.5 s     | **Padrão**. Campanhas, avisos gerais, notificações |
| `media` | 0.5 s     | Confirmações, lembretes                            |
| `alta`  | sem delay | OTP, alerta urgente, confirmação de agendamento    |

> ⚠️ **Nunca use `priority: "alta"` em envio em massa.** O WhatsApp pode bloquear o
> número de forma temporária ou permanente. "Alta" é só para mensagens individuais
> urgentes (ex: código de verificação). Se o usuário pedir disparo em lote com alta
> prioridade, recuse a configuração e explique o risco — ofereça `media` como
> alternativa para urgência razoável.

## Fluxo de trabalho

1. **Entenda a intenção** — texto simples? com anexo? disparo único ou lote? urgente?
2. **Normalize o número** para o formato `5511999999999`.
3. **Confirme o token** — se não estiver em `CHATIOPS_TOKEN`, peça ao usuário.
4. **Escolha a prioridade** — default `baixa`; só use `alta` para envio unitário
   realmente urgente; explique o trade-off se for ambíguo.
5. **Monte e execute** a chamada (JSON para texto, multipart para mídia). Use o
   script auxiliar `scripts/send_message.py` quando for conveniente.
6. **Interprete a resposta** — sucesso = `{ "mensagem": "Mensagem enviada",
   "queued": true }`. Em erro, traduza o código HTTP para linguagem clara.
7. **Verifique os headers de rate limit** (`X-DailyLimit`, `X-DailyUsed`,
   `X-DailyRemaining`) e avise o usuário se estiver chegando no limite.

## Rate limits

| Limite            | Valor         |
|-------------------|---------------|
| Por minuto        | 30 chamadas   |
| Por dia (Starter) | 20 chamadas   |
| Por dia (PRO)     | 100 chamadas  |

Para disparos em lote, **pacing**: se o usuário pedir envio para 50 contatos num
plano Starter (20/dia), avise que não vai caber e sugira plano PRO ou fracionar ao
longo de dias.

## Erros — o que cada código significa

| HTTP | Erro              | O que fazer                                               |
|------|-------------------|-----------------------------------------------------------|
| 200  | OK                | Sucesso; resposta traz `{mensagem, queued}`               |
| 400  | Bad Request       | Campo obrigatório faltando ou mal formatado (número!)     |
| 401  | Unauthorized      | Token inválido ou ausente — peça novo token ao usuário    |
| 429  | Too Many Requests | Estourou limite — espere ou aumente plano                 |
| 500  | Internal Error    | Problema no servidor Chatiops — tentar de novo em seguida |

## Webhook (receber mensagens)

O Chatiops dispara `POST` para uma URL configurada pelo usuário sempre que chega uma
nova mensagem. Payload típico:

```json
{
  "event": "message.received",
  "ticket": { "id": 123, "status": "open" },
  "contact": { "name": "João", "number": "5511999999999" },
  "message": { "body": "Olá!", "fromMe": false, "timestamp": "2026-04-17T12:00:00Z" }
}
```

A configuração do webhook é feita no painel Chatiops (**API → Configuração**), não
pela API. Se o usuário pedir ajuda para processar o payload, ajude a escrever o
handler (Node/Python/n8n) — mas o cadastro da URL é no painel.

## Scripts auxiliares

- `scripts/send_message.py` — envia texto ou mídia via linha de comando. Lê o token
  de `CHATIOPS_TOKEN` ou aceita `--token`. Use quando quiser executar algo
  deterministicamente via `bash` em vez de escrever `curl` na mão.

## Referências detalhadas

Sempre que precisar do formato exato de um payload, de um exemplo em Node/Python/
Google Apps Script ou do detalhamento dos headers de rate limit:
→ leia `references/api.md`.
