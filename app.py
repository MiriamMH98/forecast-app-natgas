import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Forecast vs Presupuesto", layout="wide")

# Mostrar logo
try:
    logo = Image.open("Logo-Natgas.png")
    st.image(logo, width=200)
except:
    st.write("")

cuentas_permitidas = [
    '6454001002 UNIFORMES VENTA',
    '6454001003 CURSOS Y CAPACITACION VENTA',
    '6454001004 ADMINISTRACION DE VIATICOS VENTA',
    '6454001005 ASESORIAS PROFESIONALES VENTA',
    '6454001007 COMISIONES FUERZA DE VENTA INTERNA',
    '6454001009 INCENTIVOS COMERCIALES EN ESPECIE',
    '6454001099 OTROS GASTOS DE PERSONAL VENTA',
    '6454002001 BONOS Y DESCUENTOS TALLERES DE CONVESION',
    '6454002002 COMISIONES FUERZA DE VENTA EXTERNA',
    '6454002003 INCENTIVOS ASESORES FUERZA EXTERNA',
    '6454002004 SERVICIOS ADICIONALES TALLERES ALIADOS',
    '6454002005 BONOS TODOS SOMOS VENTAS',
    '6454003001 PUBLICIDAD COMERCIAL Y SERVICIO AL CLIENTE',
    '6454003002 TRANSPORTE VENTA',
    '6454003003 TELEFONIA VENTA',
    '6454003004 PAPELERIA / CONSUMIBLES VENTA',
    '6454003006 SISTEMAS &  PQR',
    '6454003009 MENSAJERIA Y PAQUETERIA VENTAS',
    '6454004006 ARTICULOS PROMOCIONALES',
    '6454004007 EVENTOS COMERCIALES',
    '6454004009 REFERIDOS',
    '6454006004 APOYO DE MOVILIDAD POR GESTION COMERCIAL',
    '6454007009 BONO COMERCIAL',
    '6454007031 CURSOS Y CAPACITACIONES',
    '6454007033 ALIMENTOS',
    '6454007034 BOLETOS DE AUTOBUS',
    '6454007035 HOSPEDAJE',
    '6454007036 COMBUSTIBLES Y LUBRICANTES',
    '6454007038 BOLETOS DE AVION',
    '6454007039 TAXIS Y TRANSPORTES FORANEOS',
    '6454007041 PEAJES/CASETAS',
    '6454008099 OTROS GASTOS DE VENTA'
]

meses_es_en = {
    "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
    "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
    "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec"
}

def leer_archivo_excel(uploaded_file, anio):
    encabezados = pd.read_excel(uploaded_file, nrows=8, header=None)
    tipos = encabezados.iloc[6].ffill()
    meses = encabezados.iloc[7].ffill()
    columnas_multi = list(zip(tipos, meses))
    df = pd.read_excel(uploaded_file, skiprows=8, header=None)
    df.columns = columnas_multi
    datos = []
    for _, row in df.iterrows():
        cuenta = row[df.columns[0]]
        if cuenta not in cuentas_permitidas:
            continue
        for mes in meses_es_en:
            if ("Real", mes) in df.columns:
                valor = row[("Real", mes)]
                fecha = f"{anio}-{meses_es_en[mes]}"
                datos.append({"Cuenta": cuenta, "Fecha": fecha, "Real": valor})
    return pd.DataFrame(datos)

def leer_presupuesto(uploaded_file):
    encabezados = pd.read_excel(uploaded_file, nrows=8, header=None)
    tipos = encabezados.iloc[6].ffill()
    meses = encabezados.iloc[7].ffill()
    columnas_multi = list(zip(tipos, meses))
    df = pd.read_excel(uploaded_file, skiprows=8, header=None)
    df.columns = columnas_multi
    datos = []
    for _, row in df.iterrows():
        cuenta = row[df.columns[0]]
        if cuenta not in cuentas_permitidas:
            continue
        for mes in meses_es_en:
            if ("Presupuesto", mes) in df.columns:
                valor = row[("Presupuesto", mes)]
                fecha = pd.to_datetime(f"2025-{meses_es_en[mes]}", format="%Y-%b")
                datos.append({"Cuenta": cuenta, "Fecha": fecha, "Presupuesto": valor})
    return pd.DataFrame(datos)

def forecast_sarima(df, steps, ultima_fecha_real):
    resultados = []
    for cuenta, datos in df.groupby("Cuenta"):
        ts = datos.set_index("Fecha").sort_index()["Real"].asfreq("MS").fillna(0)
        try:
            modelo = sm.tsa.statespace.SARIMAX(ts, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12),
                                               enforce_stationarity=False, enforce_invertibility=False)
            modelo_entrenado = modelo.fit(disp=False)
            pred = modelo_entrenado.get_forecast(steps=steps)
            pred_df = pred.predicted_mean.reset_index()
            pred_df.columns = ["Fecha", "Forecast"]
            pred_df["Cuenta"] = cuenta
            pred_df = pred_df[pred_df["Fecha"] > ultima_fecha_real]
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
        leer_archivo_excel(file_2024, 2024),
        leer_archivo_excel(file_2025, 2025)
    ])
    df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"], format="%Y-%b")
    ultima_fecha_real = df_hist[df_hist["Real"] > 0]["Fecha"].max()
    pasos_forecast = 12 - ultima_fecha_real.month
    st.info(f"Última fecha real: {ultima_fecha_real.strftime('%B %Y')}. Se generará forecast para los próximos {pasos_forecast} meses.")

    if pasos_forecast > 0:
        df_forecast = forecast_sarima(df_hist, pasos_forecast, ultima_fecha_real)
        df_forecast["Forecast"] = df_forecast["Forecast"].clip(lower=0)

        df_presupuesto = leer_presupuesto(file_2025)
        bono_max = df_presupuesto[df_presupuesto['Cuenta'] == '6454007009 BONO COMERCIAL']['Presupuesto'].mean()
        df_forecast.loc[df_forecast['Cuenta'] == '6454007009 BONO COMERCIAL', 'Forecast'] =             df_forecast.loc[df_forecast['Cuenta'] == '6454007009 BONO COMERCIAL', 'Forecast'].clip(upper=bono_max)

        

resumen = pd.merge(df_forecast, df_presupuesto, on=["Cuenta", "Fecha"], how="left")
resumen = resumen.merge(
    df_hist.groupby(["Cuenta", "Fecha"])["Real"].sum().reset_index(),
    on=["Cuenta", "Fecha"],
    how="left"
)
resumen = resumen.merge(
    df_hist.groupby("Cuenta")["Real"].mean().reset_index().rename(columns={"Real": "Media_Historica_Mensual"}),
    on="Cuenta",
    how="left"
)
resumen["Comparación_vs_Histórico"] = resumen["Forecast"] - resumen["Media_Historica_Mensual"]
resumen["Comparación_Real_vs_Forecast"] = resumen["Real"] - resumen["Forecast"]
resumen["Alerta"] = resumen.apply(clasificar_alerta, axis=1)

        # Unir datos reales 2025 al resumen
        import pandas as pd
        df_reales_2025 = pd.DataFrame({"Cuenta": ["6454001002 UNIFORMES VENTA", "6454001002 UNIFORMES VENTA", "6454001002 UNIFORMES VENTA", "6454001002 UNIFORMES VENTA", "6454001003 CURSOS Y CAPACITACION VENTA", "6454001003 CURSOS Y CAPACITACION VENTA", "6454001003 CURSOS Y CAPACITACION VENTA", "6454001003 CURSOS Y CAPACITACION VENTA", "6454001004 ADMINISTRACION DE VIATICOS VENTA", "6454001004 ADMINISTRACION DE VIATICOS VENTA", "6454001004 ADMINISTRACION DE VIATICOS VENTA", "6454001004 ADMINISTRACION DE VIATICOS VENTA", "6454001005 ASESORIAS PROFESIONALES VENTA", "6454001005 ASESORIAS PROFESIONALES VENTA", "6454001005 ASESORIAS PROFESIONALES VENTA", "6454001005 ASESORIAS PROFESIONALES VENTA", "6454001007 COMISIONES FUERZA DE VENTA INTERNA", "6454001007 COMISIONES FUERZA DE VENTA INTERNA", "6454001007 COMISIONES FUERZA DE VENTA INTERNA", "6454001007 COMISIONES FUERZA DE VENTA INTERNA", "6454001009 INCENTIVOS COMERCIALES EN ESPECIE", "6454001009 INCENTIVOS COMERCIALES EN ESPECIE", "6454001009 INCENTIVOS COMERCIALES EN ESPECIE", "6454001009 INCENTIVOS COMERCIALES EN ESPECIE", "6454001099 OTROS GASTOS DE PERSONAL VENTA", "6454001099 OTROS GASTOS DE PERSONAL VENTA", "6454001099 OTROS GASTOS DE PERSONAL VENTA", "6454001099 OTROS GASTOS DE PERSONAL VENTA", "6454002001 BONOS Y DESCUENTOS TALLERES DE CONVESION", "6454002001 BONOS Y DESCUENTOS TALLERES DE CONVESION", "6454002001 BONOS Y DESCUENTOS TALLERES DE CONVESION", "6454002001 BONOS Y DESCUENTOS TALLERES DE CONVESION", "6454002002 COMISIONES FUERZA DE VENTA EXTERNA", "6454002002 COMISIONES FUERZA DE VENTA EXTERNA", "6454002002 COMISIONES FUERZA DE VENTA EXTERNA", "6454002002 COMISIONES FUERZA DE VENTA EXTERNA", "6454002003 INCENTIVOS ASESORES FUERZA EXTERNA", "6454002003 INCENTIVOS ASESORES FUERZA EXTERNA", "6454002003 INCENTIVOS ASESORES FUERZA EXTERNA", "6454002003 INCENTIVOS ASESORES FUERZA EXTERNA", "6454002004 SERVICIOS ADICIONALES TALLERES ALIADOS", "6454002004 SERVICIOS ADICIONALES TALLERES ALIADOS", "6454002004 SERVICIOS ADICIONALES TALLERES ALIADOS", "6454002004 SERVICIOS ADICIONALES TALLERES ALIADOS", "6454002005 BONOS TODOS SOMOS VENTAS", "6454002005 BONOS TODOS SOMOS VENTAS", "6454002005 BONOS TODOS SOMOS VENTAS", "6454002005 BONOS TODOS SOMOS VENTAS", "6454003002 TRANSPORTE VENTA", "6454003002 TRANSPORTE VENTA", "6454003002 TRANSPORTE VENTA", "6454003002 TRANSPORTE VENTA", "6454003003 TELEFONIA VENTA", "6454003003 TELEFONIA VENTA", "6454003003 TELEFONIA VENTA", "6454003003 TELEFONIA VENTA", "6454003004 PAPELERIA / CONSUMIBLES VENTA", "6454003004 PAPELERIA / CONSUMIBLES VENTA", "6454003004 PAPELERIA / CONSUMIBLES VENTA", "6454003004 PAPELERIA / CONSUMIBLES VENTA", "6454003006 SISTEMAS &  PQR", "6454003006 SISTEMAS &  PQR", "6454003006 SISTEMAS &  PQR", "6454003006 SISTEMAS &  PQR", "6454003009 MENSAJERIA Y PAQUETERIA VENTAS", "6454003009 MENSAJERIA Y PAQUETERIA VENTAS", "6454003009 MENSAJERIA Y PAQUETERIA VENTAS", "6454003009 MENSAJERIA Y PAQUETERIA VENTAS", "6454003001 PUBLICIDAD COMERCIAL Y SERVICIO AL CLIENTE", "6454003001 PUBLICIDAD COMERCIAL Y SERVICIO AL CLIENTE", "6454003001 PUBLICIDAD COMERCIAL Y SERVICIO AL CLIENTE", "6454003001 PUBLICIDAD COMERCIAL Y SERVICIO AL CLIENTE", "6454004006 ARTICULOS PROMOCIONALES", "6454004006 ARTICULOS PROMOCIONALES", "6454004006 ARTICULOS PROMOCIONALES", "6454004006 ARTICULOS PROMOCIONALES", "6454004007 EVENTOS COMERCIALES", "6454004007 EVENTOS COMERCIALES", "6454004007 EVENTOS COMERCIALES", "6454004007 EVENTOS COMERCIALES", "6454004009 REFERIDOS", "6454004009 REFERIDOS", "6454004009 REFERIDOS", "6454004009 REFERIDOS", "6454006004 APOYO DE MOVILIDAD POR GESTION COMERCIAL", "6454006004 APOYO DE MOVILIDAD POR GESTION COMERCIAL", "6454006004 APOYO DE MOVILIDAD POR GESTION COMERCIAL", "6454006004 APOYO DE MOVILIDAD POR GESTION COMERCIAL", "6454007009 BONO COMERCIAL", "6454007009 BONO COMERCIAL", "6454007009 BONO COMERCIAL", "6454007009 BONO COMERCIAL", "6454007031 CURSOS Y CAPACITACIONES", "6454007031 CURSOS Y CAPACITACIONES", "6454007031 CURSOS Y CAPACITACIONES", "6454007031 CURSOS Y CAPACITACIONES", "6454007033 ALIMENTOS", "6454007033 ALIMENTOS", "6454007033 ALIMENTOS", "6454007033 ALIMENTOS", "6454007034 BOLETOS DE AUTOBUS", "6454007034 BOLETOS DE AUTOBUS", "6454007034 BOLETOS DE AUTOBUS", "6454007034 BOLETOS DE AUTOBUS", "6454007035 HOSPEDAJE", "6454007035 HOSPEDAJE", "6454007035 HOSPEDAJE", "6454007035 HOSPEDAJE", "6454007036 COMBUSTIBLES Y LUBRICANTES", "6454007036 COMBUSTIBLES Y LUBRICANTES", "6454007036 COMBUSTIBLES Y LUBRICANTES", "6454007036 COMBUSTIBLES Y LUBRICANTES", "6454007038 BOLETOS DE AVION", "6454007038 BOLETOS DE AVION", "6454007038 BOLETOS DE AVION", "6454007038 BOLETOS DE AVION", "6454007039 TAXIS Y TRANSPORTES FORANEOS", "6454007039 TAXIS Y TRANSPORTES FORANEOS", "6454007039 TAXIS Y TRANSPORTES FORANEOS", "6454007039 TAXIS Y TRANSPORTES FORANEOS", "6454007041 PEAJES/CASETAS", "6454007041 PEAJES/CASETAS", "6454007041 PEAJES/CASETAS", "6454007041 PEAJES/CASETAS", "6454008099 OTROS GASTOS DE VENTA", "6454008099 OTROS GASTOS DE VENTA", "6454008099 OTROS GASTOS DE VENTA", "6454008099 OTROS GASTOS DE VENTA"], "Fecha": ["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"], "Real": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 23444.69, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 505689.67, 436479.89, 302327.58, 410536.05, 106506.89, 42282.77, 59133.79, 47127.94, 73700.0, 58600.0, 76700.0, 77000.0, 157647.42, 84405.16, 92897.36, 86120.25, 2000.0, 2000.0, 1000.0, 3000.0, 0.0, 301.64, 23612.44, 0.0, 21670.0, 21670.0, 21670.0, 23478.84, 0.0, 0.0, 4416.860000000001, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3588.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8345.0, 1550.0, 0.0, 62471.89999999997, 160568.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 725480.63, 526202.0199999998, 413893.2099999998, 492710.3600000002, 0.0, 0.0, 0.0, 0.0, 0.0, 460.12, 0.0, 157.2, 0.0, 1657.77, 0.0, 918.62, 0.0, 1919.9, 0.0, 959.95, 63401.75000000003, 62016.87000000002, 65208.53000000003, 67953.41, 0.0, 0.0, 0.0, 0.0, 9322.869999999997, 7920.040000000001, 5955.070000000002, 5377.040000000001, 561.19, 1374.1, 90.50999999999999, 1133.6, 0.0, 0.0, 0.0, 0.0]})
        df_reales_2025["Fecha"] = pd.to_datetime(df_reales_2025["Fecha"])
        resumen = pd.merge(resumen, df_reales_2025, on=["Cuenta", "Fecha"], how="left")
        resumen["Comparación_Real_vs_Forecast"] = resumen["Real"] - resumen["Forecast"]

st.success("Análisis generado correctamente ✅")
st.download_button("📥 Descargar Excel", data=generar_excel(resumen), file_name="forecast_validado.xlsx")

cuentas_disponibles = df_hist["Cuenta"].unique()
cuenta_sel = st.selectbox("Selecciona una cuenta para visualizar", cuentas_disponibles)
df_plot = df_hist[df_hist["Cuenta"] == cuenta_sel].set_index("Fecha").sort_index()
df_fore = resumen[resumen["Cuenta"] == cuenta_sel].set_index("Fecha").sort_index()

fig, ax = plt.subplots(figsize=(10, 4))
df_plot["Real"].plot(ax=ax, label="Histórico", marker='o')
df_fore["Forecast"].plot(ax=ax, label="Forecast 2025", marker='o')
df_fore["Presupuesto"].plot(ax=ax, label="Presupuesto 2025", linestyle='--')
ax.set_title(f"{cuenta_sel}")
ax.legend()
st.pyplot(fig)
