import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
from pathlib import Path

app_dir = Path(__file__).parent
datos = pd.read_csv(app_dir / "hurto_cartagena.csv", parse_dates=["fecha"])

dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
dias_largo = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
grupos_arma = {"SIN EMPLEO DE ARMAS": "Sin arma", "ARMA DE FUEGO": "Arma de fuego", "LLAVE MAESTRA": "Llave maestra"}
colores_arma = {"Sin arma": "#2E86AB", "Arma de fuego": "#C0392B", "Llave maestra": "#F39C12", "Otras": "#95A5A6"}
gris, rojo, azul = "#9DB4C0", "#C0392B", "#1F4E79"

datos["arma_grupo"] = datos["arma"].map(grupos_arma).fillna("Otras")
datos["dia"] = datos["dia_semana"].map(dict(enumerate(dias)))
datos["periodo"] = datos["fecha"].dt.to_period("M").dt.to_timestamp()

motos_matriculadas = pd.Series({2017: 66033, 2018: 67580, 2022: 70000, 2026: 70000})
motos_matriculadas = motos_matriculadas.reindex(range(2017, 2027)).interpolate()

anio_min, anio_max = int(datos["anio"].min()), int(datos["anio"].max())
anios_inicial = [anio_min, anio_max - 1]


def num(x):
    return f"{x:,.0f}".replace(",", ".")


def pct(x):
    return f"{x * 100:.1f}".replace(".", ",") + "%"


def filtrar(anios, tipo, arma):
    d = datos[datos["anio"].between(anios[0], anios[1])]
    if tipo != "Todos":
        d = d[d["tipo"] == tipo]
    sin_filtro_arma = d
    if arma != "Todas":
        d = d[d["arma_grupo"] == arma]
    return d, sin_filtro_arma


def calcular_tasa(d, anios):
    motos = d[(d["tipo"] == "Motocicletas") & (d["anio"] <= 2025)]
    lista = list(range(anios[0], min(anios[1], 2025) + 1))
    hurtos = motos.groupby("anio")["cantidad"].sum().reindex(lista, fill_value=0)
    return hurtos / motos_matriculadas.reindex(lista) * 10000


def estilo(fig, titulo, y=None):
    fig.update_layout(title=titulo, template="plotly_white", height=340, margin=dict(l=50, r=20, t=50, b=40),
                      legend=dict(orientation="h", y=-0.2), yaxis_title=y)
    return fig


def fig_mensual(d, anios):
    rango = datos[datos["anio"].between(anios[0], anios[1])]["periodo"]
    periodos = pd.date_range(rango.min(), rango.max(), freq="MS")
    serie = d.groupby("periodo")["cantidad"].sum().reindex(periodos, fill_value=0)
    fig = go.Figure()
    fig.add_bar(x=serie.index, y=serie.values, name="Hurtos por mes", marker_color=gris)
    if len(serie) >= 12:
        fig.add_scatter(x=serie.index, y=serie.rolling(12).mean(), name="Media móvil 12 meses",
                        line=dict(color=rojo, width=3))
    return estilo(fig, "Hurtos por mes", "Hurtos")


def fig_dia(d):
    s = d.groupby("dia")["cantidad"].sum().reindex(dias, fill_value=0)
    p = s / s.sum() * 100 if s.sum() else s
    fig = go.Figure(go.Bar(x=list(p.index), y=p.values, marker_color=[gris] * 5 + [rojo] * 2,
                           text=[f"{v:.1f}%" for v in p.values], textposition="outside"))
    fig.add_hline(y=100 / 7, line_dash="dash", line_color="gray", annotation_text="Reparto parejo")
    return estilo(fig, "Hurtos por día de la semana", "% de hurtos")


def fig_mes(d):
    s = d.groupby("mes")["cantidad"].sum().reindex(range(1, 13), fill_value=0)
    p = s / s.sum() * 100 if s.sum() else s
    fig = go.Figure(go.Bar(x=meses, y=p.values, marker_color=azul,
                           text=[f"{v:.1f}%" for v in p.values], textposition="outside"))
    fig.add_hline(y=100 / 12, line_dash="dash", line_color="gray", annotation_text="Reparto parejo")
    return estilo(fig, "Hurtos por mes del año", "% de hurtos")


def fig_arma(d):
    t = d.groupby(["anio", "arma_grupo"])["cantidad"].sum().unstack(fill_value=0)
    t = t.div(t.sum(axis=1), axis=0) * 100
    fig = go.Figure()
    for g in ["Sin arma", "Arma de fuego", "Llave maestra", "Otras"]:
        if g in t:
            fig.add_bar(x=[str(a) for a in t.index], y=t[g], name=g, marker_color=colores_arma[g])
    fig.update_layout(barmode="stack")
    return estilo(fig, "Tipo de arma por año (no depende del filtro de arma)", "% de hurtos")


def fig_tasa(d, anios, tipo):
    if tipo == "Automotores":
        fig = go.Figure()
        fig.add_annotation(text="La tasa se calcula solo para motocicletas", showarrow=False, font=dict(size=15))
        return estilo(fig, "Hurtos de motos por cada 10.000 motos matriculadas")
    t = calcular_tasa(d, anios)
    fig = go.Figure(go.Bar(x=[str(a) for a in t.index], y=t.values, marker_color=rojo,
                           text=[f"{v:.0f}" for v in t.values], textposition="outside"))
    return estilo(fig, "Hurtos de motos por cada 10.000 motos matriculadas", "Tasa")


def tarjeta(titulo, id_valor, color):
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.H6(titulo, className="text-muted"),
        html.H3(id=id_valor),
    ]), color=color, outline=True), width=3)


def grafico(titulo, id_grafico, ancho=6):
    return dbc.Col(dbc.Card([
        dbc.CardHeader(titulo),
        dbc.CardBody(dcc.Graph(id=id_grafico)),
    ]), width=ancho, className="mb-3")


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H1("Hurto de motos y vehículos en Cartagena", className="my-3"),
    html.P("Policía Nacional (datos.gov.co) y Cartagena Cómo Vamos. Datos desde 2017; 2026 llega hasta julio.",
           className="text-muted"),
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Años"),
                dcc.RangeSlider(id="anios", min=anio_min, max=anio_max, step=1, value=anios_inicial,
                                marks={a: str(a) for a in range(anio_min, anio_max + 1)}),
                html.Br(),
                html.Label("Tipo de vehículo"),
                dcc.Dropdown(id="tipo", options=["Todos", "Motocicletas", "Automotores"], value="Todos",
                             clearable=False),
                html.Br(),
                html.Label("Tipo de arma"),
                dcc.Dropdown(id="arma", options=["Todas", "Sin arma", "Arma de fuego", "Llave maestra", "Otras"],
                             value="Todas", clearable=False),
                html.Br(),
                dbc.Button("Reiniciar filtros", id="reset", color="secondary", outline=True, className="w-100"),
            ], className="p-3 bg-light border rounded")
        ], width=3),
        dbc.Col([
            dbc.Row([
                tarjeta("Hurtos en el periodo", "total", "primary"),
                tarjeta("Promedio mensual", "promedio", "success"),
                tarjeta("Hurtos en fin de semana", "fin", "danger"),
                tarjeta("Hurtos de motos x 10.000 motos", "tasa", "warning"),
            ], className="mb-3"),
            dbc.Card(dbc.CardBody(id="narrativa"), className="mb-3"),
            dbc.Row([grafico("Serie mensual", "g_mensual"), grafico("Tasa por 10.000 motos", "g_tasa")]),
            dbc.Row([grafico("Día de la semana", "g_dia"), grafico("Mes del año", "g_mes")]),
            dbc.Row([grafico("Tipo de arma", "g_arma", 12)]),
        ], width=9),
    ]),
], fluid=True)


@callback(
    Output("total", "children"),
    Output("promedio", "children"),
    Output("fin", "children"),
    Output("tasa", "children"),
    Output("narrativa", "children"),
    Output("g_mensual", "figure"),
    Output("g_tasa", "figure"),
    Output("g_dia", "figure"),
    Output("g_mes", "figure"),
    Output("g_arma", "figure"),
    Input("anios", "value"),
    Input("tipo", "value"),
    Input("arma", "value"),
)
def actualizar(anios, tipo, arma):
    d, sin_arma = filtrar(anios, tipo, arma)
    total = d["cantidad"].sum()
    figuras = (fig_mensual(d, anios), fig_tasa(d, anios, tipo), fig_dia(d), fig_mes(d), fig_arma(sin_arma))
    if total == 0:
        return ("0", "0", "-", "-", html.P("No hay hurtos con los filtros elegidos.", className="mb-0")) + figuras

    meses_rango = datos[datos["anio"].between(anios[0], anios[1])]["periodo"].nunique()
    prom = total / meses_rango
    fin = d[d["fin_de_semana"]]["cantidad"].sum() / total
    total_sa = sin_arma["cantidad"].sum()
    fuego = sin_arma[sin_arma["arma_grupo"] == "Arma de fuego"]["cantidad"].sum() / total_sa
    sinarma = sin_arma[sin_arma["arma_grupo"] == "Sin arma"]["cantidad"].sum() / total_sa
    por_dia = d.groupby("dia_semana")["cantidad"].sum()
    dia_pico = por_dia.idxmax()
    tasa = calcular_tasa(d, anios) if tipo != "Automotores" else pd.Series(dtype=float)

    texto = [
        f"Entre {anios[0]} y {anios[1]} se registraron {num(total)} hurtos, un promedio de {num(prom)} al mes.",
        f"El día con más hurtos es el {dias_largo[dia_pico]} ({pct(por_dia[dia_pico] / total)}). "
        f"El fin de semana concentra el {pct(fin)}; con un reparto parejo sería 28,6%.",
        f"El {pct(sinarma)} de los hurtos fue sin arma y el {pct(fuego)} con arma de fuego.",
    ]
    if len(tasa) >= 2:
        texto.append(f"La tasa de hurto de motos pasó de {tasa.iloc[0]:.0f} en {tasa.index[0]} "
                     f"a {tasa.iloc[-1]:.0f} en {tasa.index[-1]} por cada 10.000 motos.")
    narrativa = [html.P(t, className="mb-1") for t in texto]
    valor_tasa = f"{tasa.iloc[-1]:.0f} ({tasa.index[-1]})" if len(tasa) else "No aplica"
    return (num(total), num(prom), pct(fin), valor_tasa, narrativa) + figuras


@callback(
    Output("anios", "value"),
    Output("tipo", "value"),
    Output("arma", "value"),
    Input("reset", "n_clicks"),
    prevent_initial_call=True,
)
def reiniciar(n):
    return anios_inicial, "Todos", "Todas"


if __name__ == "__main__":
    app.run()
