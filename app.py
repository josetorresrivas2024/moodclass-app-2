import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import re
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MoodClass", page_icon="🎒", layout="centered")

# --- CONEXIÓN SEGURA ---
try:
    uri = st.secrets["MONGO_URI"]
except Exception:
    uri = "mongodb+srv://TU_USUARIO:TU_PASSWORD@cluster0.hzl7cg0.mongodb.net/moodclass_db?retryWrites=true&w=majority&appName=Cluster0"


@st.cache_resource
def get_database():
    client = MongoClient(uri)
    return client["moodclass_db"]


db = get_database()
col_moods = db["moods"]
col_students = db["students"]


# =========================
# FUNCIONES GENERALES
# =========================
def normalizar_texto(texto):
    return re.sub(r"\s+", " ", str(texto).strip())


def obtener_estudiantes():
    estudiantes = list(
        col_students.find({}, {"_id": 0, "name": 1, "grade": 1, "created_at": 1})
        .sort([("grade", 1), ("name", 1)])
    )
    return estudiantes


def obtener_nombres_estudiantes():
    estudiantes = obtener_estudiantes()
    return [f'{e["name"]} - {e.get("grade", "Sin grado")}' for e in estudiantes if "name" in e]


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
        return False, "Selecciona un grado."

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


def convertir_a_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Reporte")
    output.seek(0)
    return output


# =========================
# BOTIQUÍN EMOCIONAL
# =========================
def obtener_motivos_frecuentes(df, top_n=3):
    if "reason" not in df.columns:
        return []

    motivos_validos = df["reason"].fillna("").astype(str)
    motivos_validos = motivos_validos[motivos_validos.str.strip() != ""]

    if motivos_validos.empty:
        return []

    conteo = motivos_validos.value_counts().head(top_n)
    return conteo.index.tolist()


def obtener_botiquin_emocional(emocion_predominante, total_registros, porcentaje_predominante):
    if porcentaje_predominante >= 60:
        nivel = "Alta prioridad grupal"
    elif porcentaje_predominante >= 40:
        nivel = "Atención recomendada"
    else:
        nivel = "Seguimiento preventivo"

    herramientas = {
        "😊 Feliz": {
            "titulo": "Potenciar clima positivo",
            "objetivo": "Aprovechar la disposición positiva del grupo para fortalecer la participación.",
            "actividad_principal": "Ronda rápida: cada estudiante comparte algo bueno de su día en una frase.",
            "duracion": "3 a 5 minutos",
            "guia_docente": "Refuerza con mensajes breves y positivos. Usa esta energía para iniciar una actividad colaborativa.",
            "visualizacion": "Pide que recuerden un momento agradable del día y lo describan mentalmente por 20 segundos.",
            "materiales": "No requiere materiales."
        },
        "😐 Normal": {
            "titulo": "Activación suave del grupo",
            "objetivo": "Movilizar la atención y generar disposición para aprender.",
            "actividad_principal": "Pausa breve de enfoque: respiración suave por 1 minuto y estiramiento de brazos y hombros.",
            "duracion": "2 a 3 minutos",
            "guia_docente": "Haz una transición tranquila hacia la actividad principal y plantea una consigna sencilla al inicio.",
            "visualizacion": "Invita a cerrar los ojos 15 segundos y pensar: 'Estoy aquí, listo para empezar'.",
            "materiales": "No requiere materiales."
        },
        "😢 Triste": {
            "titulo": "Contención emocional breve",
            "objetivo": "Favorecer regulación emocional y sensación de acompañamiento.",
            "actividad_principal": "Pausa de escritura: escribe una palabra sobre cómo te sientes y una cosa que podría ayudarte hoy.",
            "duracion": "4 a 6 minutos",
            "guia_docente": "Valida la emoción sin presionar a compartir. Usa un tono calmado y seguro.",
            "visualizacion": "Invita a recordar un momento en que se sintieron acompañados o tranquilos.",
            "materiales": "Hoja o cuaderno y lápiz."
        },
        "😡 Molesto": {
            "titulo": "Regulación y descarga controlada",
            "objetivo": "Reducir la activación y prevenir reacciones impulsivas.",
            "actividad_principal": "Respiración + tensión-relajación: apretar puños 5 segundos y soltar, repetir 4 veces.",
            "duracion": "3 a 4 minutos",
            "guia_docente": "Evita confrontar. Marca pausas cortas y claras. Da instrucciones concretas.",
            "visualizacion": "Pide imaginar que el enojo baja lentamente como una ola que pierde fuerza.",
            "materiales": "No requiere materiales."
        },
        "😴 Cansado": {
            "titulo": "Activación corporal breve",
            "objetivo": "Recuperar energía, atención y presencia en el aula.",
            "actividad_principal": "Micropausa activa: estiramiento de cuello, hombros, brazos y respiración profunda.",
            "duracion": "2 a 4 minutos",
            "guia_docente": "Haz que todos se pongan de pie si es posible. Luego inicia con una tarea corta y clara.",
            "visualizacion": "Invita a imaginar que encienden su energía poco a poco, como una luz que aumenta.",
            "materiales": "No requiere materiales."
        }
    }

    base = herramientas.get(
        emocion_predominante,
        {
            "titulo": "Pausa breve de regulación",
            "objetivo": "Favorecer calma y disposición para continuar.",
            "actividad_principal": "Respirar profundo 5 veces y relajar hombros.",
            "duracion": "2 minutos",
            "guia_docente": "Observa al grupo antes de continuar con la actividad.",
            "visualizacion": "Invita a pensar en un lugar tranquilo por unos segundos.",
            "materiales": "No requiere materiales."
        }
    )

    return {
        "nivel": nivel,
        "emocion_predominante": emocion_predominante,
        "total_registros": total_registros,
        "porcentaje_predominante": round(porcentaje_predominante, 1),
        **base
    }


def mostrar_botiquin_emocional(df):
    if df.empty or "emotion" not in df.columns:
        st.info("No hay datos suficientes para generar el botiquín emocional.")
        return

    conteo = df["emotion"].fillna("Sin dato").value_counts()
    emocion_top = conteo.idxmax()
    cantidad_top = int(conteo.max())
    total = len(df)

    porcentaje_top = (cantidad_top / total) * 100 if total > 0 else 0
    botiquin = obtener_botiquin_emocional(emocion_top, total, porcentaje_top)
    motivos_frecuentes = obtener_motivos_frecuentes(df)

    st.markdown("### 🧰 Botiquín emocional del aula")

    col_a, col_b = st.columns(2)

    with col_a:
        st.info(
            f"**Emoción predominante:** {botiquin['emocion_predominante']}\n\n"
            f"**Incidencia:** {cantidad_top} de {total} registros ({botiquin['porcentaje_predominante']}%)\n\n"
            f"**Nivel de atención:** {botiquin['nivel']}"
        )

    with col_b:
        st.success(
            f"**Herramienta sugerida:** {botiquin['titulo']}\n\n"
            f"**Duración sugerida:** {botiquin['duracion']}"
        )

    with st.container(border=True):
        st.markdown("#### 🎯 Objetivo")
        st.write(botiquin["objetivo"])

        st.markdown("#### 🛠️ Actividad principal")
        st.write(botiquin["actividad_principal"])

        st.markdown("#### 🌿 Visualización o apoyo complementario")
        st.write(botiquin["visualizacion"])

        st.markdown("#### 👩‍🏫 Guía breve para el docente")
        st.write(botiquin["guia_docente"])

        st.markdown("#### 📎 Materiales")
        st.write(botiquin["materiales"])

        if motivos_frecuentes:
            st.markdown("#### 📌 Motivos más frecuentes del grupo")
            for motivo in motivos_frecuentes:
                st.write(f"- {motivo}")


# =========================
# DATOS DE INTERFAZ
# =========================
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

# =========================
# ESTILOS
# =========================
st.markdown("""
<style>
.card {
    padding: 18px;
    border-radius: 18px;
    background: #f7f9fc;
    border: 1px solid #e6eaf2;
    margin-bottom: 12px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
}
.card h4 {
    margin: 0;
    font-size: 16px;
    color: #374151;
}
.card h2 {
    margin: 8px 0 0 0;
    font-size: 28px;
    color: #111827;
}
.section-title {
    font-size: 20px;
    font-weight: 700;
    margin-top: 10px;
    margin-bottom: 8px;
    color: #111827;
}
</style>
""", unsafe_allow_html=True)

# =========================
# INTERFAZ
# =========================
st.title("🎒 MoodClass")
tab1, tab2 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente"])

# -------------------------
# ESTUDIANTE
# -------------------------
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

# -------------------------
# DOCENTE
# -------------------------
with tab2:
    st.subheader("🧑‍🏫 Panel docente")
    pin = st.text_input("PIN Docente", type="password")

    if pin == "1234":
        st.success("✅ Acceso autorizado")

        datos_hoy = list(col_moods.find({"day": str(date.today())}))
        estudiantes_actuales = obtener_estudiantes()

        total_registros = len(datos_hoy)
        total_estudiantes = len(estudiantes_actuales)

        emocion_top = "Sin registros"
        if datos_hoy:
            df_temp = pd.DataFrame(datos_hoy)
            if "emotion" in df_temp.columns and not df_temp["emotion"].empty:
                emocion_top = df_temp["emotion"].value_counts().idxmax()

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(f"""
            <div class="card">
                <h4>Registros de hoy</h4>
                <h2>{total_registros}</h2>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="card">
                <h4>Estudiantes registrados</h4>
                <h2>{total_estudiantes}</h2>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="card">
                <h4>Emoción más frecuente</h4>
                <h2 style="font-size:22px;">{emocion_top}</h2>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Gestión de estudiantes</div>', unsafe_allow_html=True)

        col_a, col_b = st.columns(2)

        with col_a:
            with st.container(border=True):
                st.markdown("### ➕ Agregar estudiante")
                with st.form("form_agregar_estudiante"):
                    nuevo_estudiante = st.text_input("Nombre del nuevo estudiante")
                    nuevo_grado = st.selectbox("Grado", grados_disponibles)
                    guardar_estudiante = st.form_submit_button("Agregar estudiante", use_container_width=True)

                    if guardar_estudiante:
                        ok, mensaje = agregar_estudiante(nuevo_estudiante, nuevo_grado)
                        if ok:
                            st.success(mensaje)
                            st.rerun()
                        else:
                            st.warning(mensaje)

        with col_b:
            with st.container(border=True):
                st.markdown("### 🗑️ Eliminar estudiante")
                estudiantes_actuales_labels = obtener_nombres_estudiantes()

                if estudiantes_actuales_labels:
                    with st.form("form_eliminar_estudiante"):
                        estudiante_eliminar = st.selectbox(
                            "Selecciona estudiante a eliminar",
                            estudiantes_actuales_labels
                        )
                        eliminar_btn = st.form_submit_button("Eliminar estudiante", use_container_width=True)

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

        st.markdown('<div class="section-title">Lista de estudiantes</div>', unsafe_allow_html=True)

        if estudiantes_actuales:
            df_students = pd.DataFrame(estudiantes_actuales)

            for col in ["name", "grade", "created_at"]:
                if col not in df_students.columns:
                    df_students[col] = ""

            df_students = df_students.rename(columns={
                "name": "Nombre",
                "grade": "Grado",
                "created_at": "Fecha de registro"
            })

            st.dataframe(
                df_students[["Nombre", "Grado", "Fecha de registro"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Todavía no hay estudiantes registrados.")

        st.markdown('<div class="section-title">Reporte emocional del día</div>', unsafe_allow_html=True)

        filtro1, filtro2 = st.columns(2)
        with filtro1:
            filtro_grado = st.selectbox("Filtrar por grado", ["Todos"] + grados_disponibles)
        with filtro2:
            filtro_momento = st.selectbox("Filtrar por momento", ["Todos", "Entrada", "Salida"])

        query = {"day": str(date.today())}
        if filtro_grado != "Todos":
            query["grade"] = filtro_grado
        if filtro_momento != "Todos":
            query["moment"] = filtro_momento

        datos = list(col_moods.find(query))

        if datos:
            df = pd.DataFrame(datos)

            if "emotion" not in df.columns:
                df["emotion"] = "Sin dato"

            conteo = df["emotion"].value_counts().reset_index()
            conteo.columns = ["emocion", "count"]

            fig = px.bar(
                conteo,
                x="emocion",
                y="count",
                text="count",
                color="emocion",
                title="Distribución de emociones"
            )
            fig.update_layout(
                xaxis_title="Emoción",
                yaxis_title="Cantidad",
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                title_font_size=20
            )
            st.plotly_chart(fig, use_container_width=True)

            mostrar_botiquin_emocional(df)

            st.markdown("### 📋 Registros del día")

            columnas_mostrar = ["student_name", "grade", "moment", "emotion", "reason", "timestamp"]
            for col in columnas_mostrar:
                if col not in df.columns:
                    df[col] = ""

            df_mostrar = df[columnas_mostrar].copy()
            df_mostrar.columns = ["Nombre", "Grado", "Momento", "Emoción", "Motivo", "Fecha y hora"]

            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

            excel_file = convertir_a_excel(df_mostrar)
            st.download_button(
                label="📥 Descargar reporte en Excel",
                data=excel_file,
                file_name=f"reporte_moodclass_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.info("No hay registros hoy para ese filtro.")

    elif pin != "":
        st.error("PIN incorrecto.")
