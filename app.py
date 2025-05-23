from PIL import Image

# Cargar y mostrar el logo
logo = Image.open("logo.png")
st.image(logo, width=200)
import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="Forecast vs Presupuesto", layout="wide")

cuentas_clave = [
    "6454007009 BONO COMERCIAL",
    "6454004007 EVENTOS COMERCIALES",
    "6454004006 ARTICULOS PROMOCIONALES",
    "6454002004 SERVICIOS ADICIONALES TALLERES ALIADOS",
    "6454001002 UNIFORMES VENTA"
]

meses_es_en = {
    "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
    "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
    "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec"
}

def leer_archivo_excel(uploaded_file, anio):
    encabezados = pd.read_excel(uploaded_file, nrows=8, header=None)
    tipos = encabezados.iloc[6].fillna(method='ffill')
    meses = encabezados.iloc[7].fillna(method='ffill')
    columnas_multi = list(zip(tipos, meses))
    df = pd.read_excel(uploaded_file, skiprows=8, header=None)
    df.columns = columnas_multi

    datos = []
    for _, row in df.iterrows():
        cuenta = row[df.columns[0]]
        if cuenta not in cuentas_clave:
            continue
        for mes in meses_es_en:
            if ("Real", mes) in df.columns:
                valor = row[("Real", mes)]
                fecha = f"{anio}-{meses_es_en[mes]}"
                datos.append({"Cuenta": cuenta, "Fecha": fecha, "Real": valor})
    return pd.DataFrame(datos)

def leer_presupuesto(uploaded_file):
    encabezados = pd.read_excel(uploaded_file, nrows=8, header=None)
    tipos = encabezados.iloc[6].fillna(method='ffill')
    meses = encabezados.iloc[7].fillna(method='ffill')
    columnas_multi = list(zip(tipos, meses))
    df = pd.read_excel(uploaded_file, skiprows=8, header=None)
    df.columns = columnas_multi

    datos = []
    for _, row in df.iterrows():
        cuenta = row[df.columns[0]]
        if cuenta not in cuentas_clave:
            continue
        for mes in meses_es_en:
            if ("Presupuesto", mes) in df.columns:
                valor = row[("Presupuesto", mes)]
                fecha = pd.to_datetime(f"2025-{meses_es_en[mes]}", format="%Y-%b")
                datos.append({"Cuenta": cuenta, "Fecha": fecha, "Presupuesto": valor})
    return pd.DataFrame(datos)

def forecast_sarima(df):
    resultados = []
    for cuenta, datos in df.groupby("Cuenta"):
        ts = datos.set_index("Fecha").sort_index()["Real"].asfreq("MS").fillna(0)
        try:
            modelo = sm.tsa.statespace.SARIMAX(ts, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12),
                                               enforce_stationarity=False, enforce_invertibility=False)
            modelo_entrenado = modelo.fit(disp=False)
            pred = modelo_entrenado.get_forecast(steps=12)
            pred_df = pred.predicted_mean.reset_index()
            pred_df.columns = ["Fecha", "Forecast"]
            pred_df["Cuenta"] = cuenta
            resultados.append(pred_df)
        except:
            continue
    return pd.concat(resultados)

def clasificar_alerta(row, tolerancia=0.3):
    base = row["Media_Historica_Mensual"]
    if pd.isnull(base) or base == 0:
        return "Sin datos"
    diff_pct = (row["Forecast"] - base) / base
    if diff_pct > tolerancia:
        return "🔴 Muy por encima"
    elif diff_pct < -tolerancia:
        return "🔵 Muy por debajo"
    else:
        return "🟢 En rango"

def generar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Forecast vs Presupuesto')
    output.seek(0)
    return output

st.title("📊 Forecast SARIMA vs Presupuesto 2025")

col1, col2, col3, col4 = st.columns(4)
with col1:
    file_2022 = st.file_uploader("Histórico 2022", type="xlsx")
with col2:
    file_2023 = st.file_uploader("Histórico 2023", type="xlsx")
with col3:
    file_2024 = st.file_uploader("Histórico 2024", type="xlsx")
with col4:
    file_2025 = st.file_uploader("Presupuesto 2025", type="xlsx")

if file_2022 and file_2023 and file_2024 and file_2025:
    df_hist = pd.concat([
        leer_archivo_excel(file_2022, 2022),
        leer_archivo_excel(file_2023, 2023),
        leer_archivo_excel(file_2024, 2024)
    ])
    df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"], format="%Y-%b")

    df_forecast = forecast_sarima(df_hist)
    df_forecast["Forecast"] = df_forecast["Forecast"].clip(lower=0)

    df_presupuesto = leer_presupuesto(file_2025)

    resumen = pd.merge(df_forecast, df_presupuesto, on=["Cuenta", "Fecha"], how="left")
    resumen = resumen.merge(df_hist.groupby("Cuenta")["Real"].mean().reset_index().rename(columns={"Real": "Media_Historica_Mensual"}), on="Cuenta", how="left")
    resumen["Comparación_vs_Histórico"] = resumen["Forecast"] - resumen["Media_Historica_Mensual"]
    resumen["Alerta"] = resumen.apply(clasificar_alerta, axis=1)

    st.success("Análisis generado correctamente ✅")
    st.download_button("📥 Descargar Excel", data=generar_excel(resumen), file_name="forecast_validado.xlsx")

    cuenta_sel = st.selectbox("Selecciona una cuenta para visualizar", cuentas_clave)
    df_plot = df_hist[df_hist["Cuenta"] == cuenta_sel].set_index("Fecha").sort_index()
    df_fore = resumen[resumen["Cuenta"] == cuenta_sel].set_index("Fecha").sort_index()

    fig, ax = plt.subplots(figsize=(10, 4))
    df_plot["Real"].plot(ax=ax, label="Histórico", marker='o')
    df_fore["Forecast"].plot(ax=ax, label="Forecast 2025", marker='o')
    df_fore["Presupuesto"].plot(ax=ax, label="Presupuesto 2025", linestyle='--')
    ax.set_title(f"{cuenta_sel}")
    ax.legend()
    st.pyplot(fig)
