
# 📊 Forecast App - NATGAS

Esta app permite realizar un análisis comparativo entre el forecast mensual de gastos (modelo SARIMA) y el presupuesto 2025 por línea de gasto.

Desarrollada con [Streamlit](https://streamlit.io) para análisis visual interactivo.

---

## 🧰 Funcionalidades

- Carga de históricos (2022–2024) y presupuesto 2025
- Forecast mensual por línea de gasto usando SARIMA
- Comparación con presupuesto mensual
- Alertas tipo semáforo (sobreejercicio / subejercicio)
- Visualización gráfica por cuenta
- Exportación a Excel

---

## 🚀 ¿Cómo usar?

1. Clona este repositorio o súbelo a [Streamlit Cloud](https://streamlit.io/cloud)
2. Asegúrate de tener los siguientes archivos de entrada (formato estándar NATGAS):
   - Histórico 2022, 2023, 2024 (`.xlsx`)
   - Presupuesto 2025 (`.xlsx`)

3. Ejecuta localmente con:

```bash
pip install -r requirements.txt
streamlit run app.py
```

4. O publica directamente en Streamlit Cloud conectando este repo.

---

## 📁 Estructura esperada de archivos `.xlsx`

- Encabezados en la fila 8 (`skiprows=8`)
- Columnas multinivel con nombres como:  
  `("Real", "ene")`, `("Presupuesto", "abr")`
- Cuenta en la primera columna

---

## 🧑‍💻 Contacto

Desarrollado con ❤️ para el equipo de análisis comercial de NATGAS.
