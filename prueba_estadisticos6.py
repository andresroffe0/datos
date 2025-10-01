import streamlit as st 
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from darts import TimeSeries
from darts.utils.statistics import extract_trend_and_seasonality, ModelMode
import calendar

# ---------- 1) Carga del archivo ----------
st.title("📊 Dashboard SHF Interactivo")

uploaded_file = st.file_uploader("Sube tu archivo (.csv, .xlsx, .parquet)", type=["csv", "xlsx", "parquet"])
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith(".parquet"):
        df = pd.read_parquet(uploaded_file)
    else:
        st.error("Formato no soportado")
        st.stop()

    st.write("📄 Vista previa de los datos:")
    st.dataframe(df.head())

    # ---------- 2) Selección de columnas ----------
    col_fecha = st.selectbox("Selecciona columna de FECHA", df.columns)
    col_valor = st.selectbox("Selecciona columna de CANTIDAD", df.columns)
    col_cat   = st.selectbox("Selecciona columna de CATEGORÍA", df.columns)

    # Si no hay categorías válidas, crear una ficticia
    if col_cat == col_fecha or df[col_cat].nunique() == 1 or df[col_cat].nunique() > len(df) / 2:
        df["__cat__"] = "Serie única"
        col_cat = "__cat__"

    # Convertir fechas
    df["Fecha"] = pd.to_datetime(df[col_fecha], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    df = df.sort_values([col_cat, "Fecha"])

    # ---------- 3) Frecuencia seleccionada por el usuario ----------
    mapa_freq = {
        "Diaria": "D",
        "Semanal": "W",
        "Mensual": "M",
        "Trimestral": "Q",
        "Anual": "A"
    }

    freq_es = st.selectbox("Selecciona la frecuencia de tu serie temporal", list(mapa_freq.keys()), index=2)
    freq_final = mapa_freq[freq_es]

    # ---------- 4) Cálculo de crecimiento ----------
    df["log_ind"] = np.log(df[col_valor].replace(0, np.nan))  # evitar log(0)
    df["log_lag"] = df.groupby(col_cat, observed=True)["log_ind"].diff()
    df["g"] = (np.exp(df["log_lag"]) - 1) * 100

    # ---------- 5) Periodo para boxplot con etiquetas legibles ----------
    if freq_final == "Q":
        df["Periodo"] = df["Fecha"].dt.quarter.astype(str)
        orden = ["1", "2", "3", "4"]

    elif freq_final == "M":
        meses = [calendar.month_name[m] for m in range(1, 13)]
        df["Periodo"] = df["Fecha"].dt.month.apply(lambda m: meses[m-1])
        orden = meses

    elif freq_final == "W":
        inicio_semana = df["Fecha"] - pd.to_timedelta(df["Fecha"].dt.weekday, unit="D")
        fin_semana = inicio_semana + pd.Timedelta(days=6)
        df["Periodo"] = inicio_semana.dt.strftime("%Y-%m-%d") + " – " + fin_semana.dt.strftime("%Y-%m-%d")
        orden = sorted(df["Periodo"].unique().tolist())

    elif freq_final == "A":
        df["Periodo"] = df["Fecha"].dt.year.astype(str)
        orden = sorted(df["Periodo"].unique().tolist())

    else:  # Diario
        dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        mapping = dict(zip(dias, dias_es))
        df["Periodo"] = df["Fecha"].dt.day_name().map(mapping)
        orden = dias_es

    categorias = sorted(df[col_cat].unique())
    per_cat = {}

    # ---------- Función auxiliar para elegir modelo ----------
    def elegir_modelo(ts):
        if (ts.values() <= 0).any():
            return ModelMode.ADDITIVE
        errores = {}
        for modo in [ModelMode.ADDITIVE, ModelMode.MULTIPLICATIVE]:
            try:
                trend_ts, season_ts = extract_trend_and_seasonality(
                    ts=ts,
                    freq=None,
                    model=modo,
                    method="naive"
                )
                if modo == ModelMode.ADDITIVE:
                    reconstruido = trend_ts + season_ts
                else:
                    reconstruido = trend_ts * season_ts
                err = np.mean((ts.values().ravel() - reconstruido.values().ravel())**2)
                errores[modo] = err
            except:
                errores[modo] = np.inf
        return min(errores, key=errores.get)

    for c in categorias:
        sub = df[df[col_cat] == c].copy()
        x = sub["Fecha"]

        try:
            ts = TimeSeries.from_dataframe(sub, "Fecha", col_valor, fill_missing_dates=True)
            model_mode = elegir_modelo(ts)

            trend_ts, season_ts = extract_trend_and_seasonality(
                ts=ts,
                freq=None,
                model=model_mode,
                method="naive"
            )
        except Exception as e:
            st.warning(f"No se pudo construir serie con {c}: {e}")
            continue

        def _ts_to_series(tseries):
            for method in ("pd_series", "to_series", "to_pandas", "pd_dataframe"):
                if hasattr(tseries, method):
                    res = getattr(tseries, method)()
                    if isinstance(res, pd.DataFrame) and res.shape[1] >= 1:
                        return res.iloc[:, 0]
                    return res
            vals = tseries.values()
            arr = vals[:, 0, 0] if getattr(vals, "ndim", 0) == 3 else vals.ravel()
            idx = getattr(tseries, "time_index", pd.RangeIndex(len(arr)))
            return pd.Series(arr, index=idx)

        trend_s = _ts_to_series(trend_ts).reindex(x).rename("Tendencia")
        season_s = _ts_to_series(season_ts).reindex(x).rename("Estacionalidad")

        per_cat[c] = dict(
            x=x,
            y=sub[col_valor],
            y_g=sub["g"],
            x_box=sub["Periodo"],
            y_box=sub["g"],
            y_trend=trend_s,
            y_season=season_s,
        )

    # ---------- 6) Visualización ----------
    fig = make_subplots(
        rows=5, cols=1, vertical_spacing=0.06,
        subplot_titles=(
            "Serie original",
            "Crecimiento (%)",
            "Estacionalidad",
            "Tendencia",
            "Distribución estacional (boxplot)"
        )
    )

    trace_map, trace_idx = {}, 0
    for c in categorias:
        if c not in per_cat:
            continue
        s = per_cat[c]

        fig.add_trace(go.Scatter(x=s["x"], y=s["y"], mode="lines+markers",
                                 name=f"Serie - {c}", visible=False), row=1, col=1); idx1 = trace_idx; trace_idx += 1
        fig.add_trace(go.Scatter(x=s["x"], y=s["y_g"], mode="lines+markers",
                                 name=f"Crec. - {c}", visible=False), row=2, col=1); idx2 = trace_idx; trace_idx += 1
        fig.add_trace(go.Scatter(x=s["x"], y=s["y_season"], mode="lines+markers",
                                 name=f"Estacionalidad - {c}", visible=False,
                                 marker=dict(symbol="square")), row=3, col=1); idx3 = trace_idx; trace_idx += 1
        fig.add_trace(go.Scatter(x=s["x"], y=s["y_trend"], mode="lines",
                                 name=f"Tendencia - {c}", visible=False,
                                 line=dict(dash="dash")), row=4, col=1); idx4 = trace_idx; trace_idx += 1
        fig.add_trace(go.Box(x=s["x_box"], y=s["y_box"], boxmean=True,
                             name=f"Box estacionalidad - {c}", visible=False), row=5, col=1); idx5 = trace_idx; trace_idx += 1

        trace_map[c] = [idx1, idx2, idx3, idx4, idx5]

    buttons = []
    n_traces = len(fig.data)
    for c in categorias:
        if c not in trace_map:
            continue
        vis = [False] * n_traces
        for k in trace_map[c]:
            vis[k] = True
        buttons.append(dict(
            label=c,
            method="update",
            args=[{"visible": vis}, {"title": f"Dashboard SHF - {c}"}]
        ))

    if categorias:
        inicio = categorias[0]
        if inicio in trace_map:
            initial_vis = [False] * n_traces
            for k in trace_map[inicio]:
                initial_vis[k] = True
            for i, tr in enumerate(fig.data):
                tr.visible = initial_vis[i]

        fig.update_layout(
            updatemenus=[dict(buttons=buttons, direction="down", x=0.01, y=1.12)],
            title=f"Dashboard SHF - {inicio}",
            height=1500,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )

    # Ordenar categorías del boxplot según la frecuencia
    fig.update_xaxes(categoryorder="array", categoryarray=orden, row=5, col=1)

    # Mostrar en Streamlit
    st.plotly_chart(fig, use_container_width=True)
