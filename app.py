import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MoodClass", page_icon="🎒", layout="centered")

# --- CONEXIÓN SEGURA ---
try:
    uri = st.secrets["MONGO_URI"]
except:
    uri = "mongodb+srv://TU_USUARIO:TU_PASSWORD@cluster0.hzl7cg0.mongodb.net/moodclass_db?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def get_database():
    client = MongoClient(uri)
    return client["moodclass_db"]

db = get_database()
col_moods = db["moods"]
col_students = db["students"]

# --- FUNCIONES ---
def obtener_estudiantes():
    estudiantes = list(col_students.find({}, {"_id": 0, "name": 1}).sort("name", 1))
    return [e["name"] for e in estudiantes if "name" in e]

def agregar_estudiante(nombre):
    nombre = nombre.strip()
    if not nombre:
        return False, "Escribe el nombre del estudiante."

    existe = col_students.find_one({"name": {"$regex": f"^{nombre}$", "$options": "i"}})
    if existe:
        return False, "Ese estudiante ya está registrado."

    col_students.insert_one({
        "name": nombre,
        "created_at": datetime.now()
    })
    return True, "Estudiante agregado correctamente."

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

    lista_estudiantes = obtener_estudiantes()

    if not lista_estudiantes:
        st.warning("No hay estudiantes registrados. El docente debe agregar estudiantes primero.")
    else:
        with st.form("registro_emocion"):
            nombre_estudiante = st.selectbox("Selecciona tu nombre", lista_estudiantes)
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
                motivo_final = detalle_otro.strip() if motivo == "Otro" else motivo

                if motivo == "Otro" and not motivo_final:
                    st.warning("Por favor, escribe el motivo.")
                else:
                    col_moods.insert_one({
                        "student_name": nombre_estudiante,
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
        st.success("Acceso autorizado")

        # ---- AGREGAR ESTUDIANTES ----
        st.markdown("### Agregar estudiante")
        with st.form("form_agregar_estudiante"):
            nuevo_estudiante = st.text_input("Nombre del nuevo estudiante")
            guardar_estudiante = st.form_submit_button("Agregar estudiante")

            if guardar_estudiante:
                ok, mensaje = agregar_estudiante(nuevo_estudiante)
                if ok:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.warning(mensaje)

        # ---- LISTA DE ESTUDIANTES ----
        st.markdown("### Lista de estudiantes")
        estudiantes_actuales = obtener_estudiantes()

        if estudiantes_actuales:
            df_students = pd.DataFrame({"Estudiantes": estudiantes_actuales})
            st.dataframe(df_students, use_container_width=True)
        else:
            st.info("Todavía no hay estudiantes registrados.")

        # ---- REPORTE DEL DÍA ----
        st.markdown("### Reporte emocional del día")
        datos = list(col_moods.find({"day": str(date.today())}))

        if datos:
            df = pd.DataFrame(datos)

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

            st.markdown("### Registros del día")
            columnas_mostrar = ["student_name", "moment", "emotion", "reason", "timestamp"]
            df_mostrar = df[columnas_mostrar].copy()
            df_mostrar.columns = ["Nombre", "Momento", "Emoción", "Motivo", "Fecha y hora"]

            st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.info("No hay registros hoy.")

    elif pin != "":
        st.error("PIN incorrecto.")
