# Chatiops API — Referência completa

Base URL: `https://api.chatiops.tiops.com.br`
Autenticação: `Authorization: Bearer SEU_TOKEN`

---

## 1. Enviar mensagem de texto

`POST /api/messages/send` com `Content-Type: application/json`.

### Body

| Campo         | Tipo    | Obrig. | Descrição                                   |
|---------------|---------|--------|---------------------------------------------|
| `number`      | string  | sim    | `5511999999999` (país + DDD + número)       |
| `body`        | string  | sim    | Texto da mensagem                           |
| `priority`    | string  | não    | `baixa` (padrão), `media`, `alta`           |
| `closeTicket` | boolean | não    | Fecha o ticket após enviar                  |

### Exemplo curl

```bash
curl -X POST https://api.chatiops.tiops.com.br/api/messages/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
    "number": "5511999999999",
    "body": "Olá! Esta é uma mensagem automática.",
    "priority": "baixa"
  }'
```

### Resposta (200)

```json
{ "mensagem": "Mensagem enviada", "queued": true }
```

---

## 2. Enviar mensagem com mídia (PDF, imagem, áudio, vídeo)

Mesmo endpoint, mas com `Content-Type: multipart/form-data`.

### Campos (form-data)

| Campo     | Tipo    | Obrig. | Descrição                                                   |
|-----------|---------|--------|-------------------------------------------------------------|
| `number`  | string  | sim    | Número destino                                              |
| `body`    | string  | sim    | Texto/legenda que acompanha o arquivo                       |
| `medias`  | file    | sim    | Arquivo anexo (pode ser PDF, jpg, png, mp3, mp4, etc.)      |
| `priority`| string  | não    | Igual ao envio de texto                                     |
| `closeTicket`| bool | não    | Igual ao envio de texto                                     |

### Exemplo curl

```bash
curl -X POST https://api.chatiops.tiops.com.br/api/messages/send \
  -H "Authorization: Bearer SEU_TOKEN" \
  -F "number=5511999999999" \
  -F "body=Confira o arquivo" \
  -F "medias=@/caminho/do/arquivo.pdf"
```

---

## 3. Campo `priority`

| Valor   | Delay     | Uso recomendado                                   |
|---------|-----------|---------------------------------------------------|
| `baixa` | 1.5 s     | Padrão. Envio normal, campanhas, notificações     |
| `media` | 0.5 s     | Confirmações, lembretes                           |
| `alta`  | sem delay | Confirmação de agendamento, OTP, alertas urgentes |

> ⚠️ `priority: "alta"` em massa → **banimento do número pelo WhatsApp**. Use apenas
> para mensagens individuais urgentes.

---

## 4. Webhook (receber mensagens)

Configure no painel em **API → Configuração**, colando a URL do seu endpoint (ex:
`https://seusite.com/webhook`). O Chatiops envia `POST` para essa URL em cada
mensagem recebida.

### Payload

```json
{
  "event": "message.received",
  "ticket": { "id": 123, "status": "open" },
  "contact": { "name": "João", "number": "5511999999999" },
  "message": {
    "body": "Olá!",
    "fromMe": false,
    "timestamp": "2026-04-17T12:00:00Z"
  }
}
```

### Exemplo de handler em Node/Express

```js
app.post('/webhook', (req, res) => {
  const { event, contact, message } = req.body;
  if (event === 'message.received' && !message.fromMe) {
    console.log(`Recebida de ${contact.name}: ${message.body}`);
    // sua lógica aqui — ex: classificar, responder, criar ticket em outro sistema
  }
  res.sendStatus(200);
});
```

### Exemplo de handler em Python/Flask

```python
from flask import Flask, request

app = Flask(__name__)

@app.post('/webhook')
def webhook():
    data = request.get_json()
    if data.get('event') == 'message.received' and not data['message']['fromMe']:
        print(f"Recebida de {data['contact']['name']}: {data['message']['body']}")
    return '', 200
```

---

## 5. Rate limits

| Limite            | Valor         |
|-------------------|---------------|
| Por minuto        | 30 chamadas   |
| Por dia (Starter) | 20 chamadas   |
| Por dia (PRO)     | 100 chamadas  |

### Headers de resposta

Toda resposta bem-sucedida traz:

```
X-DailyLimit: 100
X-DailyUsed: 15
X-DailyRemaining: 85
```

Quando `X-DailyRemaining` estiver perto de zero, pare os envios e avise o usuário.
Quando estourar, a próxima chamada volta `429 Too Many Requests`.

---

## 6. Códigos de erro

| HTTP | Erro              | Descrição / ação                                             |
|------|-------------------|---------------------------------------------------------------|
| 200  | —                 | Sucesso. Mensagem aceita e entrou na fila.                    |
| 400  | Bad Request       | Campos obrigatórios faltando, número mal formatado            |
| 401  | Unauthorized      | Token inválido ou ausente — gere novo token no painel         |
| 429  | Too Many Requests | Excedeu 30/min ou limite diário do plano                      |
| 500  | Internal Error    | Problema no servidor — tente novamente em alguns segundos     |

---

## 7. Exemplos de integração

### Node.js (axios)

```js
const axios = require('axios');

await axios.post('https://api.chatiops.tiops.com.br/api/messages/send', {
  number: '5511999999999',
  body: 'Olá do Node.js!',
  priority: 'alta'
}, {
  headers: { Authorization: 'Bearer SEU_TOKEN' }
});
```

### Python (requests)

```python
import requests

requests.post(
    'https://api.chatiops.tiops.com.br/api/messages/send',
    json={'number': '5511999999999', 'body': 'Olá do Python!', 'priority': 'alta'},
    headers={'Authorization': 'Bearer SEU_TOKEN'}
)
```

### Google Apps Script (disparar a partir de planilha)

```js
function enviarWhatsApp() {
  UrlFetchApp.fetch('https://api.chatiops.tiops.com.br/api/messages/send', {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer SEU_TOKEN' },
    payload: JSON.stringify({
      number: '5511999999999',
      body: 'Olá do Google Sheets!'
    })
  });
}
```

### n8n / Make / Zapier

Use o nó genérico **HTTP Request** com:

- **URL:** `https://api.chatiops.tiops.com.br/api/messages/send`
- **Method:** `POST`
- **Header:** `Authorization: Bearer SEU_TOKEN`
- **Body type:** JSON (ou Form-Data se for anexar arquivo)
- **Campos:** `number`, `body`, `priority` (opcional)

---

## 8. Perguntas que o Claude deve saber responder

**"O token expira?"**
Não. Só é invalidado se você gerar outro ou revogar manualmente no painel.

**"Posso usar o mesmo token em dois sistemas diferentes?"**
Tecnicamente sim, mas os rate limits são compartilhados. Prefira uma conexão por
sistema para isolar.

**"Por que minha mensagem entrou na fila mas não chegou?"**
A resposta `queued: true` significa que foi aceita pela API. A entrega depende da
sessão WhatsApp estar conectada. Peça para o usuário conferir o status da conexão
no painel.

**"Posso agendar envio?"**
A API não tem agendamento nativo — dispara na hora da chamada. Para agendar, use um
cron/scheduler externo (n8n, Zapier, cron do seu servidor) que chame a API no horário
desejado.
