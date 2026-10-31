#!/usr/bin/env python3
"""Gera assets/atividade.svg com os números e o mapa de contribuições do perfil.

Uso:
    GITHUB_TOKEN=... GITHUB_USER=joa-no python3 scripts/gerar_atividade.py
    python3 scripts/gerar_atividade.py --vazio     # card sem dados (estado inicial)

Só usa a biblioteca padrão do Python.
"""
import html
import json
import os
import sys
import urllib.request
from pathlib import Path

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
BG, BORDER = "#0d1117", "#2a3140"
BODY, MUTED, ACCENT = "#c4ccd6", "#9da7b3", "#a594f9"
NIVEIS = ["#1a2030", "#3b3470", "#5a4db0", "#7b6ce0", "#a594f9"]
MAPA_NIVEL = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER) { totalCount }
    pullRequests { totalCount }
    issues(states: OPEN) { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionLevel } }
      }
    }
  }
}
"""


def consultar(token, login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "gerar-atividade",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        raise RuntimeError(f"Erro na API do GitHub: {payload.get('errors')}")
    u = payload["data"]["user"]
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    return {
        "total": cal["totalContributions"],
        "repos": u["repositories"]["totalCount"],
        "commits": cc["totalCommitContributions"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "semanas": [
            [
                (d["weekday"], MAPA_NIVEL.get(d["contributionLevel"], 0))
                for d in w["contributionDays"]
            ]
            for w in cal["weeks"]
        ],
        "datas": [[d["date"] for d in w["contributionDays"]] for w in cal["weeks"]],
    }


def vazio():
    return {
        "total": None,
        "repos": None,
        "commits": None,
        "prs": None,
        "issues": None,
        "semanas": [[(d, 0) for d in range(7)] for _ in range(53)],
        "datas": None,
    }


def numero(n):
    return "–" if n is None else f"{n:,}".replace(",", ".")


def icones():
    s = f'fill="none" stroke="{MUTED}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
    return [
        f'<g {s}><polyline points="2,10 5.5,10 8,3.5 11,15 13.5,8 16,8"/></g>',
        f'<g {s}><rect x="3.5" y="2.5" width="11" height="13" rx="2"/><line x1="6.5" y1="6.5" x2="11.5" y2="6.5"/><line x1="6.5" y1="10" x2="10" y2="10"/></g>',
        f'<g {s}><circle cx="9" cy="9" r="7"/><polyline points="9,5 9,9 12,11"/></g>',
        f'<g {s}><circle cx="4.5" cy="4" r="1.8"/><circle cx="4.5" cy="14" r="1.8"/><circle cx="14" cy="14" r="1.8"/><line x1="4.5" y1="5.8" x2="4.5" y2="12.2"/><path d="M14 12.2V9.5Q14 5.5 10 5.5H8"/></g>',
        f'<g {s}><circle cx="9" cy="9" r="7"/><circle cx="9" cy="9" r="1.6" fill="{MUTED}"/></g>',
    ]


def renderizar(d):
    W, H = 980, 240
    gx, gy, passo, cel = 362, 78, 11, 8
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="Atividade no GitHub" font-family="{FONT}">',
        "  <title>Atividade no GitHub</title>",
        f'  <rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{BG}" stroke="{BORDER}"/>',
    ]

    # números
    linhas = [
        ("Total de contribuições", d["total"]),
        ("Repositórios públicos", d["repos"]),
        ("Commits (último ano)", d["commits"]),
        ("Pull requests", d["prs"]),
        ("Issues abertas", d["issues"]),
    ]
    for i, (rotulo, valor) in enumerate(linhas):
        y = 52 + i * 37
        out.append(f'  <g transform="translate(28 {y-14})">{icones()[i]}</g>')
        out.append(f'  <text x="58" y="{y}" font-size="15" fill="{BODY}">{html.escape(rotulo)}</text>')
        out.append(
            f'  <text x="280" y="{y}" font-size="15" font-weight="600" text-anchor="end" fill="{ACCENT}">{numero(valor)}</text>'
        )
    out.append(f'  <line x1="304" y1="26" x2="304" y2="{H-26}" stroke="{BORDER}"/>')

    # mapa de contribuições
    out.append(f'  <text x="330" y="40" font-size="14" fill="{MUTED}">Contribuições nos últimos 365 dias</text>')
    for r, nome in ((1, "Seg"), (3, "Qua"), (5, "Sex")):
        out.append(
            f'  <text x="330" y="{gy + r*passo + cel - 0.5}" font-size="11.5" fill="{MUTED}">{nome}</text>'
        )
    ultimo_mes_x = -99
    for c, semana in enumerate(d["semanas"]):
        x = gx + c * passo
        if d["datas"] and d["datas"][c]:
            mes = int(d["datas"][c][0][5:7]) - 1
            anterior = int(d["datas"][c - 1][0][5:7]) - 1 if c and d["datas"][c - 1] else None
            if mes != anterior and x - ultimo_mes_x >= 40:
                out.append(f'  <text x="{x}" y="{gy-9}" font-size="11.5" fill="{MUTED}">{MESES[mes]}</text>')
                ultimo_mes_x = x
        for dia, nivel in semana:
            out.append(
                f'  <rect x="{x}" y="{gy + dia*passo}" width="{cel}" height="{cel}" rx="2" fill="{NIVEIS[nivel]}"/>'
            )

    # legenda
    ly = gy + 7 * passo + 22
    fim = gx + 53 * passo - 3
    xm = fim - 26
    out.append(f'  <text x="{fim}" y="{ly+8}" font-size="11.5" text-anchor="end" fill="{MUTED}">Mais</text>')
    for k in range(5):
        out.append(
            f'  <rect x="{xm - 6 - (5-k)*passo + 3:.0f}" y="{ly}" width="{cel}" height="{cel}" rx="2" fill="{NIVEIS[k]}"/>'
        )
    out.append(
        f'  <text x="{xm - 6 - 5*passo:.0f}" y="{ly+8}" font-size="11.5" text-anchor="end" fill="{MUTED}">Menos</text>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    destino = Path(__file__).resolve().parent.parent / "assets" / "atividade.svg"
    destino.parent.mkdir(parents=True, exist_ok=True)
    if "--vazio" in sys.argv:
        dados = vazio()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        login = os.environ.get("GITHUB_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER")
        if not token or not login:
            sys.exit("Defina GITHUB_TOKEN e GITHUB_USER (ou use --vazio).")
        dados = consultar(token, login)
    destino.write_text(renderizar(dados), encoding="utf-8")
    print(f"Gerado: {destino}")


if __name__ == "__main__":
    main()
