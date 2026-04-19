#!/usr/bin/env python3
"""
Envia mensagem WhatsApp via API Chatiops.

Uso rápido:

    # texto
    CHATIOPS_TOKEN=xxx python send_message.py \\
        --number 5511999999999 \\
        --body "Olá!"

    # texto com prioridade
    python send_message.py --token xxx -n 5511999999999 -b "OTP: 123456" -p alta

    # anexar arquivo
    python send_message.py -n 5511999999999 -b "Segue seu boleto" -f boleto.pdf

    # fechar ticket após enviar
    python send_message.py -n 5511999999999 -b "Atendimento encerrado" --close

O token pode vir via --token ou via variável de ambiente CHATIOPS_TOKEN.
Em caso de erro, o script sai com código != 0 e imprime a mensagem.

Depende apenas de `requests` (biblioteca padrão de HTTP em Python).
Instale com: pip install requests --break-system-packages
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.stderr.write(
        "Falta a biblioteca 'requests'. Instale com:\n"
        "    pip install requests --break-system-packages\n"
    )
    sys.exit(2)


BASE_URL = "https://api.chatiops.tiops.com.br"
ENDPOINT = f"{BASE_URL}/api/messages/send"
VALID_PRIORITIES = {"baixa", "media", "alta"}


def normalize_number(raw: str) -> str:
    """Remove tudo que não for dígito. Não adivinha o país — se veio sem 55 o
    usuário é quem sabe."""
    cleaned = re.sub(r"\D", "", raw)
    if not cleaned:
        raise ValueError(f"Número inválido: {raw!r}")
    return cleaned


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Envia mensagem WhatsApp via API Chatiops",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-n", "--number", required=True,
                   help="Número destino (ex: 5511999999999)")
    p.add_argument("-b", "--body", required=True,
                   help="Texto da mensagem (ou legenda se houver --file)")
    p.add_argument("-f", "--file", dest="file_path",
                   help="Caminho de arquivo para anexar (PDF/imagem/áudio/vídeo)")
    p.add_argument("-p", "--priority", choices=sorted(VALID_PRIORITIES),
                   default="baixa",
                   help="Prioridade do envio (padrão: baixa)")
    p.add_argument("--close", action="store_true",
                   help="Fecha o ticket após enviar")
    p.add_argument("--token",
                   help="Token Bearer. Se omitido, usa CHATIOPS_TOKEN do ambiente.")
    return p


def resolve_token(cli_token: str | None) -> str:
    token = cli_token or os.environ.get("CHATIOPS_TOKEN")
    if not token:
        sys.stderr.write(
            "Token não encontrado. Passe --token ou exporte CHATIOPS_TOKEN.\n"
        )
        sys.exit(2)
    return token


def send(
    token: str,
    number: str,
    body: str,
    priority: str = "baixa",
    close_ticket: bool = False,
    file_path: str | None = None,
) -> dict:
    headers = {"Authorization": f"Bearer {token}"}

    if file_path:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        data = {
            "number": number,
            "body": body,
            "priority": priority,
        }
        if close_ticket:
            data["closeTicket"] = "true"
        with path.open("rb") as fh:
            files = {"medias": (path.name, fh)}
            resp = requests.post(ENDPOINT, headers=headers, data=data, files=files)
    else:
        payload = {
            "number": number,
            "body": body,
            "priority": priority,
        }
        if close_ticket:
            payload["closeTicket"] = True
        headers["Content-Type"] = "application/json"
        resp = requests.post(ENDPOINT, headers=headers, json=payload)

    # Rate limit info: expõe para o caller
    rate_info = {
        "daily_limit": resp.headers.get("X-DailyLimit"),
        "daily_used": resp.headers.get("X-DailyUsed"),
        "daily_remaining": resp.headers.get("X-DailyRemaining"),
    }

    if resp.status_code == 200:
        result = resp.json()
        result["_rate_limit"] = rate_info
        return result

    # Erros — traduz para mensagens claras
    reasons = {
        400: "Campos obrigatórios faltando ou número mal formatado.",
        401: "Token inválido ou ausente. Gere um novo token no painel Chatiops.",
        429: "Limite de envios atingido (30/min ou limite diário do plano).",
        500: "Erro interno no servidor Chatiops. Tente novamente em instantes.",
    }
    reason = reasons.get(resp.status_code, "Erro desconhecido.")
    try:
        detail = resp.json()
    except Exception:
        detail = resp.text
    raise RuntimeError(
        f"HTTP {resp.status_code} — {reason}\n"
        f"Resposta do servidor: {detail}\n"
        f"Rate limit: {rate_info}"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token = resolve_token(args.token)

    try:
        number = normalize_number(args.number)
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        return 2

    try:
        result = send(
            token=token,
            number=number,
            body=args.body,
            priority=args.priority,
            close_ticket=args.close,
            file_path=args.file_path,
        )
    except FileNotFoundError as e:
        sys.stderr.write(f"{e}\n")
        return 2
    except RuntimeError as e:
        sys.stderr.write(f"{e}\n")
        return 1

    print("Mensagem enviada com sucesso.")
    rate = result.get("_rate_limit", {})
    remaining = rate.get("daily_remaining")
    if remaining is not None:
        print(f"Envios restantes hoje: {remaining}/{rate.get('daily_limit')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
