# -*- coding: utf-8 -*-
"""
Painel Dash - Previsão personalizada (Divino)

Lê arquivos PNG na pasta do próprio app, com nomes:
    divino_prec_YYYY-MM-DD.png
    divino_prec_acumulada_YYYY-MM-DD_a_YYYY-MM-DD.png

E também um PNG fixo (gráfico 4 pontos):
    prec_4_pontos_2x2.png

Permite:
- Ver mapa diário de precipitação
- Ver animação ao longo dos dias (todos os arquivos encontrados)
- Ver o mapa de precipitação acumulada no período

Ao abrir o site:
- Mostra o gráfico fixo (4 pontos) à esquerda
- Mostra o mapa com controles à direita
"""

from pathlib import Path
import base64
from datetime import datetime

from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# ----------------- CONFIGURAÇÕES ----------------- #

# Local das figuras (mesmo diretório do app.py)
IMG_DIR = Path(__file__).parent

# Nome do PNG fixo (4 pontos)
FIXO_4PONTOS_PNG = "prec_4_pontos_2x2.png"

# Pontos de foco (coordenadas normalizadas 0–1 na imagem) - opcional
PONTOS_FOCO = {
    # Exemplo:
    # "Casa": {"x": 0.45, "y": 0.60},
}

# ----------------- VARIÁVEIS DISPONÍVEIS ----------------- #

VAR_OPCOES = {
    "prec": {
        "label": "Precipitação diária (mm)",
        "prefix": "divino_prec_",
        "usa_data": True,
    },
    "prec_acum": {
        "label": "Precipitação acumulada no período (mm)",
        "prefix": "divino_prec_acumulada_",
        "usa_data": False,  # ignora dropdown de data
    },
}

# ----------------- FUNÇÕES AUXILIARES ----------------- #

def listar_datas_disponiveis():
    """
    Procura arquivos:
        divino_prec_YYYY-MM-DD.png
    e usa o sufixo YYYY-MM-DD como 'data_tag'.
    """
    if not IMG_DIR.exists():
        raise FileNotFoundError(f"Pasta de imagens não encontrada: {IMG_DIR}")

    datas = set()
    for img_path in IMG_DIR.glob("divino_prec_*.png"):
        stem = img_path.stem  # ex.: 'divino_prec_2025-11-13'
        parte_data = stem.replace("divino_prec_", "", 1)
        try:
            datetime.strptime(parte_data, "%Y-%m-%d")
            datas.add(parte_data)
        except ValueError:
            continue

    return sorted(datas)


def formatar_label_br(data_iso: str) -> str:
    """Converte '2025-11-13' -> '13/11/2025'."""
    dt = datetime.strptime(data_iso, "%Y-%m-%d")
    return dt.strftime("%d/%m/%Y")


def carregar_imagem_base64(var_key: str, data_iso: str | None = None) -> str:
    """
    Lê o arquivo PNG correspondente à variável e data,
    converte em base64 para embutir no Dash.

    Para 'prec_acum', ignora data_iso e pega o arquivo acumulado mais recente.
    """
    info = VAR_OPCOES[var_key]
    prefix = info["prefix"]

    if var_key == "prec_acum":
        candidates = sorted(IMG_DIR.glob(f"{prefix}*.png"))
        if not candidates:
            print(f"⚠️ Nenhuma imagem de precipitação acumulada encontrada com padrão {prefix}*.png")
            return ""
        img_path = candidates[-1]
    else:
        if data_iso is None:
            return ""
        img_path = IMG_DIR / f"{prefix}{data_iso}.png"

    if not img_path.exists():
        print(f"⚠️ Arquivo não encontrado: {img_path}")
        return ""

    with open(img_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")

    return f"data:image/png;base64,{encoded}"


def carregar_png_fixo_base64(nome_arquivo: str) -> str:
    """Carrega um PNG fixo no diretório do app e retorna base64."""
    img_path = IMG_DIR / nome_arquivo
    if not img_path.exists():
        print(f"⚠️ PNG fixo não encontrado: {img_path}")
        return ""
    with open(img_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def adicionar_pontos_foco(fig: go.Figure) -> go.Figure:
    """Adiciona marcadores dos pontos de foco."""
    if not PONTOS_FOCO:
        return fig

    xs = [info["x"] for info in PONTOS_FOCO.values()]
    ys = [info["y"] for info in PONTOS_FOCO.values()]
    labels = list(PONTOS_FOCO.keys())

    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            text=labels,
            textposition="top center",
            marker=dict(
                size=10,
                symbol="circle-open-dot",
                line=dict(width=2),
            ),
            hovertemplate="%{text}<extra></extra>",
        )
    )
    return fig


def construir_figura_estatica(src: str, titulo: str) -> go.Figure:
    """Figura estática com a imagem base64 + pontos de foco."""
    fig = go.Figure()

    if not src:
        fig.update_layout(
            title=titulo,
            xaxis={"visible": False},
            yaxis={"visible": False},
            margin=dict(l=0, r=0, t=40, b=0),
            paper_bgcolor="white",
            plot_bgcolor="white",
        )
        return fig

    fig.add_layout_image(
        dict(
            source=src,
            xref="x",
            yref="y",
            x=0,
            y=1,
            sizex=1,
            sizey=1,
            sizing="stretch",
            layer="below",
        )
    )

    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1], scaleanchor="x")

    fig = adicionar_pontos_foco(fig)

    fig.update_layout(
        title=titulo,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


def construir_animacao(var_key: str, datas_iso: list[str]) -> go.Figure:
    """Constrói animação para campo diário."""
    fig = go.Figure()

    # frame inicial
    src0 = carregar_imagem_base64(var_key, datas_iso[0])
    fig.add_layout_image(
        dict(
            source=src0,
            xref="x",
            yref="y",
            x=0,
            y=1,
            sizex=1,
            sizey=1,
            sizing="stretch",
            layer="below",
        )
    )

    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1], scaleanchor="x")

    # frames
    frames = []
    for d in datas_iso:
        src = carregar_imagem_base64(var_key, d)
        frames.append(
            go.Frame(
                name=d,
                layout=dict(
                    images=[
                        dict(
                            source=src,
                            xref="x",
                            yref="y",
                            x=0,
                            y=1,
                            sizex=1,
                            sizey=1,
                            sizing="stretch",
                            layer="below",
                        )
                    ],
                ),
            )
        )

    fig.frames = frames

    slider_steps = [
        dict(
            method="animate",
            args=[
                [f.name],
                {
                    "mode": "immediate",
                    "frame": {"duration": 500, "redraw": True},
                    "transition": {"duration": 0},
                },
            ],
            label=formatar_label_br(f.name),
        )
        for f in frames
    ]

    sliders = [
        dict(
            active=0,
            steps=slider_steps,
            x=0.1,
            y=0,
            len=0.9,
            pad={"t": 30, "b": 10},
            currentvalue={"prefix": "Data: "},
            transition={"duration": 0},
        )
    ]

    updatemenus = [
        dict(
            type="buttons",
            showactive=False,
            x=0.0,
            y=1.05,
            xanchor="left",
            yanchor="top",
            buttons=[
                dict(
                    label="▶ Play",
                    method="animate",
                    args=[
                        None,
                        {
                            "frame": {"duration": 500, "redraw": True},
                            "fromcurrent": True,
                            "transition": {"duration": 0},
                        },
                    ],
                )
            ],
        )
    ]

    fig = adicionar_pontos_foco(fig)

    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=40),
        dragmode="pan",
        sliders=sliders,
        updatemenus=updatemenus,
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


# ----------------- DATAS ----------------- #

DATAS = listar_datas_disponiveis()
if not DATAS:
    raise RuntimeError(
        f"Nenhuma data diária encontrada em {IMG_DIR}. "
        f"Certifique-se de gerar os arquivos divino_prec_YYYY-MM-DD.png primeiro."
    )

DATA_DEFAULT = DATAS[-1]

# ----------------- APP DASH ----------------- #

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # usado pelo gunicorn
app.title = "Previsão de Chuva - Divino"

# figura fixa (4 pontos) calculada uma vez no startup
src_fixo = carregar_png_fixo_base64(FIXO_4PONTOS_PNG)
fig_fixo = construir_figura_estatica(src_fixo, "Precipitação prevista (mm/dia) — 4 pontos")

app.layout = dbc.Container(
    [
        html.H2(
            "Previsão de Chuva - Painel Divino",
            className="mt-3 mb-2",
            style={"textAlign": "center"},
        ),

        html.Div(
            "Visualização diária e acumulada de precipitação a partir da previsão ECMWF (HRES).",
            className="mb-3",
            style={"textAlign": "center"},
        ),

        dbc.Row(
            [
                # --------- ESQUERDA: GRÁFICO FIXO ---------
                dbc.Col(
                    [
                        html.H5("Gráfico fixo (4 pontos)", className="mb-2"),
                        dcc.Graph(
                            id="graph-4pontos",
                            figure=fig_fixo,
                            style={"height": "85vh"},
                            config={"displayModeBar": False},
                        ),
                        html.Small(
                            f"Arquivo: {FIXO_4PONTOS_PNG} (coloque na mesma pasta do app.py).",
                            className="text-muted",
                        ),
                    ],
                    md=5,
                    lg=5,
                    xl=5,
                ),

                # --------- DIREITA: CONTROLES + MAPA ---------
                dbc.Col(
                    [
                        html.H5("Mapa e controles", className="mb-2"),

                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Label("Tipo de mapa:", className="fw-bold"),
                                    dcc.RadioItems(
                                        id="radio-var",
                                        options=[
                                            {"label": v["label"], "value": k}
                                            for k, v in VAR_OPCOES.items()
                                        ],
                                        value="prec",
                                        inline=False,
                                        className="mb-3",
                                    ),

                                    html.Label("Data da previsão:", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="dropdown-data",
                                        options=[
                                            {"label": formatar_label_br(d), "value": d}
                                            for d in DATAS
                                        ],
                                        value=DATA_DEFAULT,
                                        clearable=False,
                                        className="mb-3",
                                    ),

                                    html.Label("Modo de visualização:", className="fw-bold"),
                                    dcc.RadioItems(
                                        id="radio-modo",
                                        options=[
                                            {"label": "Mapa diário", "value": "dia"},
                                            {"label": "Animação (todos os dias)", "value": "anim"},
                                        ],
                                        value="dia",
                                        inline=False,
                                    ),
                                    html.Small(
                                        "Obs: Animação só se aplica ao campo diário. "
                                        "Para o acumulado, sempre será um mapa estático.",
                                        className="text-muted",
                                    ),
                                ]
                            ),
                            className="mb-2",
                        ),

                        dcc.Graph(
                            id="graph-mapa",
                            style={"height": "75vh"},
                            config={
                                "scrollZoom": True,
                                "displayModeBar": False,
                            },
                        ),
                    ],
                    md=7,
                    lg=7,
                    xl=7,
                ),
            ],
            className="mb-3",
        ),

        html.Hr(),
        html.Footer(
            "Fonte: ECMWF Open Data – Processamento local (Pedro / Dash)",
            className="text-muted mt-1 mb-2",
            style={"fontSize": "0.85rem"},
        ),
    ],
    fluid=True,
)

# ----------------- CALLBACK ----------------- #

@app.callback(
    Output("graph-mapa", "figure"),
    Input("dropdown-data", "value"),
    Input("radio-var", "value"),
    Input("radio-modo", "value"),
)
def atualizar_mapa(data_iso, var_key, modo):
    if var_key is None:
        return go.Figure()

    info = VAR_OPCOES[var_key]

    # Acumulado: sempre estático
    if var_key == "prec_acum":
        src = carregar_imagem_base64("prec_acum", None)
        return construir_figura_estatica(src, info["label"])

    # Diário
    if modo == "dia":
        if data_iso is None:
            return go.Figure()
        label_data = formatar_label_br(data_iso)
        titulo = f"{info['label']} – {label_data}"
        src = carregar_imagem_base64(var_key, data_iso)
        return construir_figura_estatica(src, titulo)
    else:
        return construir_animacao(var_key, DATAS)

# ----------------- MAIN (apenas local) ----------------- #

if __name__ == "__main__":
    print("Painel Divino rodando em http://127.0.0.1:8050/")
    app.run(host="0.0.0.0", port=8050, debug=True)




if __name__ == "__main__":
    # rodar local
    app.run(host="0.0.0.0", port=8050, debug=True)
