"""Panel web con Streamlit:  streamlit run app.py"""
import pandas as pd
import streamlit as st

import core

st.set_page_config(page_title="Mi inversión", page_icon="📈", layout="wide")

est, car = core.cargar_estrategia(), core.cargar_carteras()
m = est["moneda"]
desv = core.desviaciones(car, est)
total = sum(d.valor for d in desv)

st.title(f"📈 {est['nombre']}")
if core.usando_ejemplo():
    st.info("Mostrando datos de ejemplo. Crea `carteras.yaml` con tus posiciones.")

c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio", core.eur(total, m))
c2.metric("Aportación mensual", core.eur(est["aportacion_mensual"], m), f"día {est['dia_aportacion']}")
rebal = core.necesita_rebalanceo(car, est)
c3.metric("¿Rebalancear?", "Sí ⚠️" if rebal else "No ✅", f"banda ±{est['banda_rebalanceo']} pp",
          delta_color="off")

st.subheader("Reparto actual vs objetivo")
df = pd.DataFrame([{
    "Clase": core.nombre_clase(d.clase), "Actual %": round(d.actual, 1),
    "Objetivo %": d.objetivo, "Diferencia pp": round(d.diferencia, 1),
    "Valor": round(d.valor, 2), "Fuera de banda": "🔴" if d.fuera_banda else "🟢",
} for d in desv])
izq, der = st.columns([3, 2])
izq.bar_chart(df.set_index("Clase")[["Actual %", "Objetivo %"]], stack=False)
der.dataframe(df, hide_index=True, width="stretch")

if rebal:
    st.warning("Hay clases fuera de banda. Primero corrige con aportaciones; vender es el último recurso.")
    mov = core.rebalanceo_completo(car, est)
    st.dataframe(pd.DataFrame([{"Clase": core.nombre_clase(c), "Comprar(+)/Vender(-)": round(v, 2)}
                               for c, v in mov.items()]), hide_index=True)
else:
    st.success("Todo dentro de la banda. **La decisión correcta es no hacer nada.**")

st.subheader("💶 Calculadora de aportación")
importe = st.number_input("Importe a invertir", min_value=0.0, value=float(est["aportacion_mensual"]), step=50.0)
if importe:
    rep = core.reparto_aportacion(car, est, importe)
    st.dataframe(pd.DataFrame([{"Clase": core.nombre_clase(c), "Importe": round(v, 2)} for c, v in rep.items()]),
                 hide_index=True)

st.subheader("🏦 Carteras")
pos = pd.DataFrame(core.posiciones(car))
for nombre, grupo in pos.groupby("cartera", sort=False):
    with st.expander(f"{nombre} – {core.eur(grupo['valor'].sum(), m)}"):
        st.dataframe(grupo[["nombre", "ticker", "clase", "participaciones", "precio", "valor"]],
                     hide_index=True, width="stretch")

st.subheader("🧭 Reglas que no se negocian")
for r in est["reglas"]:
    st.markdown(f"- {r}")

st.subheader("📝 Diario de decisiones")
d = core.diario()
if d:
    st.dataframe(pd.DataFrame(d), hide_index=True, width="stretch")
    st.caption(f"🛡️ Impulsos frenados: {sum(o['estado'] == 'descartada' for o in d)}")
else:
    st.caption("Sin entradas. Usa /quiero en el bot antes de cualquier operación fuera del plan.")
