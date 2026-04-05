import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MoodClass", page_icon="🎒", layout="centered")

# --- CONEXIÓN SEGURA ---
try:
    if "MONGO_URI" in st.secrets:
        uri = st.secrets["MONGO_URI"]
    else:
        uri = "mongodb+srv://TU_USUARIO:TU_PASSWORD@cluster0.hzl7cg0.mongodb.net/moodclass_db?retryWrites=true&w=majority&appName=Cluster0"
except:
    uri = "mongodb+srv://TU_USUARIO:TU_PASSWORD@cluster0.hzl7cg0.mongodb.net/moodclass_db?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def get_database():
    client = MongoClient(uri)
    return client["moodclass_db"]

db = get_database()
col_moods = db["moods"]

# --- OPCIONES DE MOTIVOS POR EMOCIÓN ---
motivos_por_emocion = {
    "😊 Feliz": [
        "Me fue bien en clase",
        "Jugué con mis amigos",
        "Mi familia me apoyó",
        "Aprendí algo nuevo",
        "Tuve un buen día",
        "Otro"
    ],
    "😐 Normal": [
        "Todo estuvo tranquilo",
        "Fue un día común",
        "No pasó nada especial",
        "Me siento estable",
        "Otro"
    ],
    "😢 Triste": [
        "Tuve un problema en casa",
        "Discutí con un amigo",
        "Me fue mal en una tarea",
        "Me siento solo(a)",
        "Extraño a alguien",
        "Otro"
    ],
    "😡 Molesto": [
        "Me molestaron",
        "Discutí con alguien",
        "No salió algo como quería",
        "Tuve un mal momento",
        "Otro"
    ],
    "😴 Cansado": [
        "Dormí poco",
        "Tuve muchas actividades",
        "Estoy agotado(a)",
        "Fue un día pesado",
        "Otro"
    ]
}

# --- INTERFAZ ---
st.title("🎒 MoodClass")
tab1, tab2 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente"])

# ---------------- ESTUDIANTE ----------------
with tab1:
    st.subheader("Registro emocional del estudiante")

    with st.form("registro_emocion"):
        nombre_estudiante = st.text_input("Nombre del estudiante")
        momento = st.selectbox("Momento", ["Entrada", "Salida"])
        emocion = st.selectbox(
            "¿Cómo te sientes?",
            ["😊 Feliz", "😐 Normal", "😢 Triste", "😡 Molesto", "😴 Cansado"]
        )

        motivo = st.selectbox(
            "¿Por qué te sientes así?",
            motivos_por_emocion[emocion]
        )

        detalle_otro = ""
        if motivo == "Otro":
            detalle_otro = st.text_area("Escribe el motivo")

        guardar = st.form_submit_button("Guardar Estado")

        if guardar:
            if not nombre_estudiante.strip():
                st.warning("Por favor, escribe el nombre del estudiante.")
            else:
                motivo_final = detalle_otro.strip() if motivo == "Otro" else motivo

                if motivo == "Otro" and not motivo_final:
                    st.warning("Por favor, escribe el motivo.")
                else:
                    col_moods.insert_one({
                        "student_name": nombre_estudiante.strip(),
                        "day": str(date.today()),
                        "moment": momento,
                        "emotion": emocion,
                        "reason": motivo_final,
                        "timestamp": datetime.now()
                    })
                    st.success("¡Estado guardado correctamente!")

# ---------------- DOCENTE ----------------
with tab2:
    st.subheader("Panel docente")
    pin = st.text_input("PIN Docente", type="password")

    if pin == "1234":
        datos = list(col_moods.find({"day": str(date.today())}))

        if datos:
            df = pd.DataFrame(datos)

            # Gráfico de emociones
            conteo = df["emotion"].value_counts().reset_index()
            conteo.columns = ["emocion", "count"]

            fig = px.bar(
                conteo,
                x="emocion",
                y="count",
                color="emocion",
                title="Emociones registradas hoy"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabla de registros
            st.subheader("Registros del día")

            columnas_mostrar = ["student_name", "moment", "emotion", "reason", "timestamp"]
            df_mostrar = df[columnas_mostrar].copy()
            df_mostrar.columns = ["Nombre", "Momento", "Emoción", "Motivo", "Fecha y hora"]

            st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.info("No hay registros hoy.")

    elif pin != "":
        st.error("PIN incorrecto.")
