import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import re

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
def normalizar_texto(texto):
    return re.sub(r"\s+", " ", texto.strip())

def obtener_estudiantes():
    estudiantes = list(
        col_students.find({}, {"_id": 0, "name": 1, "grade": 1}).sort([("grade", 1), ("name", 1)])
    )
    return estudiantes

def obtener_nombres_estudiantes():
    estudiantes = obtener_estudiantes()
    return [f'{e["name"]} - {e.get("grade", "Sin grado")}' for e in estudiantes]

def buscar_estudiante_por_label(label):
    estudiantes = obtener_estudiantes()
    for e in estudiantes:
        actual = f'{e["name"]} - {e.get("grade", "Sin grado")}'
        if actual == label:
            return e
    return None

def agregar_estudiante(nombre, grado):
    nombre = normalizar_texto(nombre)
    grado = normalizar_texto(grado)

    if not nombre:
        return False, "Escribe el nombre del estudiante."

    if not grado:
        return False, "Selecciona o escribe el grado."

    existe = col_students.find_one({
        "name": {"$regex": f"^{re.escape(nombre)}$", "$options": "i"},
        "grade": {"$regex": f"^{re.escape(grado)}$", "$options": "i"}
    })

    if existe:
        return False, "Ese estudiante ya está registrado en ese grado."

    col_students.insert_one({
        "name": nombre,
        "grade": grado,
        "created_at": datetime.now()
    })
    return True, "Estudiante agregado correctamente."

def eliminar_estudiante(nombre, grado):
    resultado = col_students.delete_one({"name": nombre, "grade": grado})
    if resultado.deleted_count > 0:
        return True, "Estudiante eliminado correctamente."
    return False, "No se pudo eliminar el estudiante."

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

grados_disponibles = [
    "1ro Primaria",
    "2do Primaria",
    "3ro Primaria",
    "4to Primaria",
    "5to Primaria",
    "6to Primaria",
    "1ro Secundaria",
    "2do Secundaria",
    "3ro Secundaria",
    "4to Secundaria",
    "5to Secundaria"
]

# --- INTERFAZ ---
st.title("🎒 MoodClass")
tab1, tab2 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente"])

# ---------------- ESTUDIANTE ----------------
with tab1:
    st.subheader("Registro emocional del estudiante")

    lista_estudiantes = obtener_nombres_estudiantes()

    if not lista_estudiantes:
        st.warning("No hay estudiantes registrados. El docente debe agregar estudiantes primero.")
    else:
        with st.form("registro_emocion"):
            estudiante_label = st.selectbox("Selecciona tu nombre", lista_estudiantes)

            estudiante_data = buscar_estudiante_por_label(estudiante_label)
            grado_estudiante = estudiante_data.get("grade", "") if estudiante_data else ""

            st.text_input("Grado", value=grado_estudiante, disabled=True)

            momento = st.selectbox("Momento", ["Entrada", "Salida"])
            emocion = st.selectbox(
                "¿Cómo te sientes?",
                ["😊 Feliz", "😐 Normal", "😢 Triste", "😡 Molesto", "😴 Cansado"]
            )

            motivo = st.selectbox("¿Por qué te sientes así?", motivos_por_emocion[emocion])

            detalle_otro = ""
            if motivo == "Otro":
                detalle_otro = st.text_area("Escribe el motivo")

            guardar = st.form_submit_button("Guardar Estado")

            if guardar:
                motivo_final = detalle_otro.strip() if motivo == "Otro" else motivo

                if motivo == "Otro" and not motivo_final:
                    st.warning("Por favor, escribe el motivo.")
                elif estudiante_data is None:
                    st.error("No se encontró el estudiante seleccionado.")
                else:
                    col_moods.insert_one({
                        "student_name": estudiante_data["name"],
                        "grade": estudiante_data.get("grade", ""),
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

        col_a, col_b = st.columns(2)

        # ---- AGREGAR ESTUDIANTE ----
        with col_a:
            st.markdown("### Agregar estudiante")
            with st.form("form_agregar_estudiante"):
                nuevo_estudiante = st.text_input("Nombre del nuevo estudiante")
                nuevo_grado = st.selectbox("Grado", grados_disponibles)
                guardar_estudiante = st.form_submit_button("Agregar estudiante")

                if guardar_estudiante:
                    ok, mensaje = agregar_estudiante(nuevo_estudiante, nuevo_grado)
                    if ok:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.warning(mensaje)

        # ---- ELIMINAR ESTUDIANTE ----
        with col_b:
            st.markdown("### Eliminar estudiante")
            estudiantes_actuales_labels = obtener_nombres_estudiantes()

            if estudiantes_actuales_labels:
                with st.form("form_eliminar_estudiante"):
                    estudiante_eliminar = st.selectbox(
                        "Selecciona estudiante a eliminar",
                        estudiantes_actuales_labels
                    )
                    eliminar_btn = st.form_submit_button("Eliminar estudiante")

                    if eliminar_btn:
                        estudiante_data = buscar_estudiante_por_label(estudiante_eliminar)
                        if estudiante_data:
                            ok, mensaje = eliminar_estudiante(
                                estudiante_data["name"],
                                estudiante_data.get("grade", "")
                            )
                            if ok:
                                st.success(mensaje)
                                st.rerun()
                            else:
                                st.warning(mensaje)
                        else:
                            st.error("No se encontró el estudiante.")
            else:
                st.info("No hay estudiantes para eliminar.")

        # ---- LISTA DE ESTUDIANTES ----
        st.markdown("### Lista de estudiantes")
        estudiantes_actuales = obtener_estudiantes()

        if estudiantes_actuales:
            df_students = pd.DataFrame(estudiantes_actuales)
            df_students = df_students.rename(columns={
                "name": "Nombre",
                "grade": "Grado"
            })
            if "created_at" in df_students.columns:
                df_students = df_students[["Nombre", "Grado", "created_at"]]
                df_students = df_students.rename(columns={"created_at": "Fecha de registro"})
            st.dataframe(df_students, use_container_width=True)
        else:
            st.info("Todavía no hay estudiantes registrados.")

        # ---- FILTRO POR GRADO ----
        st.markdown("### Reporte emocional del día")
        filtro_grado = st.selectbox("Filtrar por grado", ["Todos"] + grados_disponibles)

        query = {"day": str(date.today())}
        if filtro_grado != "Todos":
            query["grade"] = filtro_grado

        datos = list(col_moods.find(query))

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
            columnas_mostrar = ["student_name", "grade", "moment", "emotion", "reason", "timestamp"]
            df_mostrar = df[columnas_mostrar].copy()
            df_mostrar.columns = ["Nombre", "Grado", "Momento", "Emoción", "Motivo", "Fecha y hora"]
            st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.info("No hay registros hoy para ese filtro.")

    elif pin != "":
        st.error("PIN incorrecto.")
