import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import re
from io import BytesIO

# ======================================
# CONFIGURACIÓN DE PÁGINA
# ======================================
st.set_page_config(page_title="MoodClass", page_icon="🎒", layout="centered")

# ======================================
# CONEXIÓN A MONGODB
# ======================================
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

# ======================================
# FUNCIONES GENERALES
# ======================================
def normalizar_texto(texto):
    return re.sub(r"\s+", " ", str(texto).strip())


def obtener_grado_seguro(valor):
    if valor is None or str(valor).strip() == "":
        return "Sin grado"
    return str(valor).strip()


def obtener_estudiantes():
    estudiantes = list(
        col_students.find({}, {"name": 1, "grade": 1, "created_at": 1})
        .sort([("grade", 1), ("name", 1)])
    )
    return estudiantes


def obtener_nombres_estudiantes():
    estudiantes = obtener_estudiantes()
    nombres = []

    for e in estudiantes:
        if "name" in e:
            grado = obtener_grado_seguro(e.get("grade"))
            nombres.append(f'{e["name"]} - {grado}')

    return nombres


def buscar_estudiante_por_label(label):
    estudiantes = obtener_estudiantes()

    for e in estudiantes:
        grado = obtener_grado_seguro(e.get("grade"))
        actual = f'{e["name"]} - {grado}'
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


def eliminar_estudiante(student_id):
    resultado = col_students.delete_one({"_id": student_id})

    if resultado.deleted_count > 0:
        return True, "Estudiante eliminado correctamente."
    return False, "No se pudo eliminar el estudiante."


def convertir_a_excel(df, nombre_hoja="Reporte"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=nombre_hoja)
    output.seek(0)
    return output


def numero_a_nombre_mes(numero_mes):
    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    return meses.get(numero_mes, f"Mes {numero_mes}")


def texto_mes_anio(year, month):
    return f"{numero_a_nombre_mes(month)} {year}"


def obtener_opciones_meses():
    registros = list(col_moods.find({}, {"_id": 0, "month": 1, "year": 1}))
    opciones = set()

    for r in registros:
        month = r.get("month")
        year = r.get("year")
        if month and year:
            opciones.add((year, month))

    if not opciones:
        hoy = datetime.now()
        opciones.add((hoy.year, hoy.month))

    return sorted(list(opciones), reverse=True)


def obtener_dataframe_mensual(year, month, grado="Todos", momento="Todos"):
    query = {"year": year, "month": month}

    if grado != "Todos":
        query["grade"] = grado
    if momento != "Todos":
        query["moment"] = momento

    datos = list(col_moods.find(query).sort("timestamp", -1))
    return pd.DataFrame(datos) if datos else pd.DataFrame()


def preparar_tabla_registros(df):
    columnas_mostrar = ["student_name", "grade", "day", "moment", "emotion", "reason", "timestamp"]

    for col in columnas_mostrar:
        if col not in df.columns:
            df[col] = ""

    df_mostrar = df[columnas_mostrar].copy()
    df_mostrar["grade"] = df_mostrar["grade"].apply(obtener_grado_seguro)

    df_mostrar.columns = ["Nombre", "Grado", "Fecha", "Momento", "Emoción", "Motivo", "Fecha y hora"]
    return df_mostrar


def construir_comparacion_meses(df_mes_1, nombre_mes_1, df_mes_2, nombre_mes_2):
    emociones_base = ["😊 Feliz", "😐 Normal", "😢 Triste", "😡 Molesto", "😴 Cansado", "😰 Ansioso", "😟Preocupado"]

    conteo_1 = df_mes_1["emotion"].value_counts() if not df_mes_1.empty and "emotion" in df_mes_1.columns else pd.Series(dtype=int)
    conteo_2 = df_mes_2["emotion"].value_counts() if not df_mes_2.empty and "emotion" in df_mes_2.columns else pd.Series(dtype=int)

    filas = []
    for emocion in emociones_base:
        filas.append({
            "Emoción": emocion,
            nombre_mes_1: int(conteo_1.get(emocion, 0)),
            nombre_mes_2: int(conteo_2.get(emocion, 0))
        })

    return pd.DataFrame(filas)


# ======================================
# BOTIQUÍN EMOCIONAL
# ======================================
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
        },
        "😟 Preocupado": {
        "titulo": "Canalizar la preocupación",
        "objetivo": "Ayudar a los estudiantes a identificar y expresar sus preocupaciones para reducir la carga emocional.",
        "actividad_principal": "Semáforo de preocupaciones: escriben en un papel algo que les preocupa (rojo), algo que pueden controlar (amarillo) y una acción posible (verde).",
        "duracion": "5 a 7 minutos",
        "guia_docente": "Escucha sin juzgar. Valida emociones y guía a enfocarse en lo que sí pueden controlar.",
        "visualizacion": "Pide que imaginen guardando su preocupación en una caja y cerrándola por un momento para poder concentrarse.",
        "materiales": "Hojas pequeñas o post-its y lápices."
        
        },
        "😰 Ansioso": {
        "titulo": "Regular la ansiedad",
        "objetivo": "Reducir la activación emocional mediante técnicas breves de respiración y enfoque.",
        "actividad_principal": "Respiración 4-4-4: inhalar 4 segundos, sostener 4, exhalar 4 (repetir 4 veces).",
        "duracion": "3 a 5 minutos",
        "guia_docente": "Habla con voz calmada, marca el ritmo de la respiración y acompaña el ejercicio con pausas.",
        "visualizacion": "Invita a imaginar una ola que sube al inhalar y baja al exhalar, siguiendo el ritmo de la respiración.",
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


# ======================================
# DATOS DE INTERFAZ
# ======================================
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

# ======================================
# ESTILOS
# ======================================
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
    margin-top: 12px;
    margin-bottom: 10px;
    color: #111827;
}
</style>
""", unsafe_allow_html=True)

# ======================================
# INTERFAZ PRINCIPAL
# ======================================
st.title("🎒 MoodClass")
tab1, tab2 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente"])

# ======================================
# PESTAÑA ESTUDIANTE
# ======================================
with tab1:
    st.subheader("Registro emocional del estudiante")

    lista_estudiantes = obtener_nombres_estudiantes()

    if not lista_estudiantes:
        st.warning("No hay estudiantes registrados. El docente debe agregar estudiantes primero.")
    else:
        with st.form("registro_emocion"):
            estudiante_label = st.selectbox("Selecciona tu nombre", lista_estudiantes)

            estudiante_data = buscar_estudiante_por_label(estudiante_label)
            grado_estudiante = obtener_grado_seguro(estudiante_data.get("grade")) if estudiante_data else ""

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
                hoy = datetime.now()

                if motivo == "Otro" and not motivo_final:
                    st.warning("Por favor, escribe el motivo.")
                elif estudiante_data is None:
                    st.error("No se encontró el estudiante seleccionado.")
                else:
                    col_moods.insert_one({
                        "student_name": estudiante_data["name"],
                        "grade": obtener_grado_seguro(estudiante_data.get("grade")),
                        "day": str(date.today()),
                        "month": hoy.month,
                        "year": hoy.year,
                        "moment": momento,
                        "emotion": emocion,
                        "reason": motivo_final,
                        "timestamp": hoy
                    })
                    st.success("¡Estado guardado correctamente!")

# ======================================
# PESTAÑA DOCENTE
# ======================================
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

        # ======================================
        # GESTIÓN DE ESTUDIANTES
        # ======================================
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
                                ok, mensaje = eliminar_estudiante(estudiante_data["_id"])
                                if ok:
                                    st.success("✅ Estudiante eliminado correctamente")
                                    st.rerun()
                                else:
                                    st.error(mensaje)
                            else:
                                st.error("No se encontró el estudiante.")
                else:
                    st.info("No hay estudiantes para eliminar.")

        # ======================================
        # LISTA DE ESTUDIANTES
        # ======================================
        st.markdown('<div class="section-title">Lista de estudiantes</div>', unsafe_allow_html=True)

        if estudiantes_actuales:
            df_students = pd.DataFrame(estudiantes_actuales)

            for col in ["name", "grade", "created_at"]:
                if col not in df_students.columns:
                    df_students[col] = ""

            df_students["name"] = df_students["name"].fillna("")
            df_students["grade"] = df_students["grade"].apply(obtener_grado_seguro)
            df_students["created_at"] = df_students["created_at"].fillna("")

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

        # ======================================
        # REPORTE DEL DÍA
        # ======================================
        st.markdown('<div class="section-title">Reporte emocional del día</div>', unsafe_allow_html=True)

        filtro1, filtro2 = st.columns(2)

        with filtro1:
            filtro_grado = st.selectbox("Filtrar por grado", ["Todos"] + grados_disponibles, key="dia_grado")
        with filtro2:
            filtro_momento = st.selectbox("Filtrar por momento", ["Todos", "Entrada", "Salida"], key="dia_momento")

        query = {"day": str(date.today())}
        if filtro_grado != "Todos":
            query["grade"] = filtro_grado
        if filtro_momento != "Todos":
            query["moment"] = filtro_momento

        datos = list(col_moods.find(query).sort("timestamp", -1))

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
                title="Distribución de emociones del día"
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
            df_mostrar = preparar_tabla_registros(df)
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

            excel_file = convertir_a_excel(df_mostrar, "Reporte_Dia")
            st.download_button(
                label="📥 Descargar reporte del día en Excel",
                data=excel_file,
                file_name=f"reporte_moodclass_dia_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.info("No hay registros hoy para ese filtro.")

        # ======================================
        # REPORTE MENSUAL
        # ======================================
        st.markdown('<div class="section-title">Reporte emocional por mes</div>', unsafe_allow_html=True)

        opciones_meses = obtener_opciones_meses()
        opciones_meses_texto = [texto_mes_anio(y, m) for y, m in opciones_meses]
        mapa_meses = {texto_mes_anio(y, m): (y, m) for y, m in opciones_meses}

        col_m1, col_m2, col_m3 = st.columns(3)

        with col_m1:
            mes_seleccionado_texto = st.selectbox("Selecciona el mes", opciones_meses_texto, key="mes_unico")
        with col_m2:
            filtro_grado_mes = st.selectbox("Filtrar grado", ["Todos"] + grados_disponibles, key="mes_grado")
        with col_m3:
            filtro_momento_mes = st.selectbox("Filtrar momento", ["Todos", "Entrada", "Salida"], key="mes_momento")

        year_sel, month_sel = mapa_meses[mes_seleccionado_texto]
        df_mes = obtener_dataframe_mensual(year_sel, month_sel, filtro_grado_mes, filtro_momento_mes)

        if not df_mes.empty:
            if "emotion" not in df_mes.columns:
                df_mes["emotion"] = "Sin dato"

            conteo_mes = df_mes["emotion"].value_counts().reset_index()
            conteo_mes.columns = ["emocion", "count"]

            fig_mes = px.bar(
                conteo_mes,
                x="emocion",
                y="count",
                text="count",
                color="emocion",
                title=f"Distribución de emociones - {mes_seleccionado_texto}"
            )
            fig_mes.update_layout(
                xaxis_title="Emoción",
                yaxis_title="Cantidad",
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                title_font_size=20
            )
            st.plotly_chart(fig_mes, use_container_width=True)

            mostrar_botiquin_emocional(df_mes)

            st.markdown("### 📋 Registros del mes")
            df_mes_mostrar = preparar_tabla_registros(df_mes)
            st.dataframe(df_mes_mostrar, use_container_width=True, hide_index=True)

            excel_mes = convertir_a_excel(df_mes_mostrar, "Reporte_Mensual")
            st.download_button(
                label="📥 Descargar reporte mensual en Excel",
                data=excel_mes,
                file_name=f"reporte_mensual_{year_sel}_{month_sel}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="descarga_mensual"
            )
        else:
            st.info("No hay registros para ese mes y filtros seleccionados.")

        # ======================================
        # COMPARACIÓN DE MESES
        # ======================================
        st.markdown('<div class="section-title">Comparar meses</div>', unsafe_allow_html=True)

        col_c1, col_c2 = st.columns(2)

        with col_c1:
            mes_1_texto = st.selectbox("Primer mes", opciones_meses_texto, key="comparacion_mes_1")
        with col_c2:
            indice_segundo = 1 if len(opciones_meses_texto) > 1 else 0
            mes_2_texto = st.selectbox("Segundo mes", opciones_meses_texto, index=indice_segundo, key="comparacion_mes_2")

        comp_f1, comp_f2 = st.columns(2)

        with comp_f1:
            filtro_grado_comp = st.selectbox("Filtrar grado comparación", ["Todos"] + grados_disponibles, key="comp_grado")
        with comp_f2:
            filtro_momento_comp = st.selectbox("Filtrar momento comparación", ["Todos", "Entrada", "Salida"], key="comp_momento")

        y1, m1 = mapa_meses[mes_1_texto]
        y2, m2 = mapa_meses[mes_2_texto]

        df_mes_1 = obtener_dataframe_mensual(y1, m1, filtro_grado_comp, filtro_momento_comp)
        df_mes_2 = obtener_dataframe_mensual(y2, m2, filtro_grado_comp, filtro_momento_comp)

        tabla_comparacion = construir_comparacion_meses(df_mes_1, mes_1_texto, df_mes_2, mes_2_texto)

        if not tabla_comparacion.empty:
            tabla_larga = tabla_comparacion.melt(
                id_vars="Emoción",
                var_name="Mes",
                value_name="Cantidad"
            )

            fig_comp = px.bar(
                tabla_larga,
                x="Emoción",
                y="Cantidad",
                color="Mes",
                barmode="group",
                text="Cantidad",
                title=f"Comparación de emociones: {mes_1_texto} vs {mes_2_texto}"
            )
            fig_comp.update_layout(
                xaxis_title="Emoción",
                yaxis_title="Cantidad",
                plot_bgcolor="white",
                paper_bgcolor="white",
                title_font_size=20
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            st.markdown("### 📊 Tabla comparativa")
            st.dataframe(tabla_comparacion, use_container_width=True, hide_index=True)

            excel_comp = convertir_a_excel(tabla_comparacion, "Comparacion_Meses")
            st.download_button(
                label="📥 Descargar comparación en Excel",
                data=excel_comp,
                file_name=f"comparacion_{y1}_{m1}_vs_{y2}_{m2}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="descarga_comparacion"
            )

            total_1 = len(df_mes_1)
            total_2 = len(df_mes_2)

            cc1, cc2 = st.columns(2)
            with cc1:
                st.info(f"**{mes_1_texto}**\n\nTotal de registros: **{total_1}**")
            with cc2:
                st.info(f"**{mes_2_texto}**\n\nTotal de registros: **{total_2}**")
        else:
            st.info("No hay datos para comparar.")

        # ======================================
        # REPORTE POR ESTUDIANTE O GRUPO
        # ======================================
        st.markdown('<div class="section-title">Seguimiento emocional individual y grupal</div>', unsafe_allow_html=True)

        with st.container(border=True):
            estudiantes_labels = ["Grupo completo"] + obtener_nombres_estudiantes()

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)

            with col_r1:
                tipo_reporte = st.selectbox(
                    "Tipo de reporte",
                    ["Por día", "Por mes"],
                    key="tipo_reporte_estudiante"
                )

            with col_r2:
                estudiante_seleccionado = st.selectbox(
                    "Selecciona estudiante o grupo",
                    estudiantes_labels,
                    key="estudiante_reporte"
                )

            with col_r3:
                filtro_grado_est = st.selectbox(
                    "Filtrar grado",
                    ["Todos"] + grados_disponibles,
                    key="grado_reporte_estudiante"
                )

            with col_r4:
                filtro_momento_est = st.selectbox(
                    "Filtrar momento",
                    ["Todos", "Entrada", "Salida"],
                    key="momento_reporte_estudiante"
                )

            query_est = {}

            if estudiante_seleccionado != "Grupo completo":
                estudiante_data = buscar_estudiante_por_label(estudiante_seleccionado)
                if estudiante_data:
                    query_est["student_name"] = estudiante_data["name"]

            if filtro_grado_est != "Todos":
                query_est["grade"] = filtro_grado_est

            if filtro_momento_est != "Todos":
                query_est["moment"] = filtro_momento_est

            if tipo_reporte == "Por día":
                fecha_reporte = st.date_input(
                    "Selecciona la fecha",
                    value=date.today(),
                    key="fecha_reporte_individual"
                )

                query_est["day"] = str(fecha_reporte)
                datos_est = list(col_moods.find(query_est).sort("timestamp", -1))

                if datos_est:
                    df_est = pd.DataFrame(datos_est)

                    if "emotion" not in df_est.columns:
                        df_est["emotion"] = "Sin dato"

                    titulo_reporte = (
                        f"Reporte diario de {estudiante_seleccionado}"
                        if estudiante_seleccionado != "Grupo completo"
                        else "Reporte diario del grupo completo"
                    )

                    st.markdown(f"### {titulo_reporte}")

                    mx1, mx2, mx3 = st.columns(3)
                    with mx1:
                        st.metric("Total registros", len(df_est))
                    with mx2:
                        emocion_top_est = df_est["emotion"].value_counts().idxmax()
                        st.metric("Emoción más frecuente", emocion_top_est)
                    with mx3:
                        estudiantes_unicos = df_est["student_name"].nunique() if "student_name" in df_est.columns else 0
                        st.metric("Estudiantes con registros", estudiantes_unicos)

                    conteo_est = df_est["emotion"].value_counts().reset_index()
                    conteo_est.columns = ["emocion", "count"]

                    fig_est = px.bar(
                        conteo_est,
                        x="emocion",
                        y="count",
                        text="count",
                        color="emocion",
                        title=f"Distribución de emociones - {fecha_reporte}"
                    )
                    fig_est.update_layout(
                        xaxis_title="Emoción",
                        yaxis_title="Cantidad",
                        showlegend=False,
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        title_font_size=20
                    )
                    st.plotly_chart(fig_est, use_container_width=True)

                    mostrar_botiquin_emocional(df_est)

                    df_est_mostrar = preparar_tabla_registros(df_est)
                    st.dataframe(df_est_mostrar, use_container_width=True, hide_index=True)

                    excel_est = convertir_a_excel(df_est_mostrar, "Reporte_Diario")
                    st.download_button(
                        label="📥 Descargar reporte diario en Excel",
                        data=excel_est,
                        file_name=f"reporte_diario_{fecha_reporte}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="descargar_reporte_diario_estudiante"
                    )
                else:
                    st.info("No hay registros para esa fecha con los filtros seleccionados.")

            else:
                opciones_meses_est = obtener_opciones_meses()
                opciones_meses_est_texto = [texto_mes_anio(y, m) for y, m in opciones_meses_est]
                mapa_meses_est = {texto_mes_anio(y, m): (y, m) for y, m in opciones_meses_est}

                mes_est_texto = st.selectbox(
                    "Selecciona el mes del reporte",
                    opciones_meses_est_texto,
                    key="mes_reporte_individual"
                )

                year_est, month_est = mapa_meses_est[mes_est_texto]
                query_est["year"] = year_est
                query_est["month"] = month_est

                datos_est = list(col_moods.find(query_est).sort("timestamp", -1))

                if datos_est:
                    df_est = pd.DataFrame(datos_est)

                    if "emotion" not in df_est.columns:
                        df_est["emotion"] = "Sin dato"

                    titulo_reporte = (
                        f"Reporte mensual de {estudiante_seleccionado}"
                        if estudiante_seleccionado != "Grupo completo"
                        else "Reporte mensual del grupo completo"
                    )

                    st.markdown(f"### {titulo_reporte}")

                    mx1, mx2, mx3 = st.columns(3)
                    with mx1:
                        st.metric("Total registros", len(df_est))
                    with mx2:
                        emocion_top_est = df_est["emotion"].value_counts().idxmax()
                        st.metric("Emoción más frecuente", emocion_top_est)
                    with mx3:
                        estudiantes_unicos = df_est["student_name"].nunique() if "student_name" in df_est.columns else 0
                        st.metric("Estudiantes con registros", estudiantes_unicos)

                    conteo_est = df_est["emotion"].value_counts().reset_index()
                    conteo_est.columns = ["emocion", "count"]

                    fig_est = px.bar(
                        conteo_est,
                        x="emocion",
                        y="count",
                        text="count",
                        color="emocion",
                        title=f"Distribución de emociones - {mes_est_texto}"
                    )
                    fig_est.update_layout(
                        xaxis_title="Emoción",
                        yaxis_title="Cantidad",
                        showlegend=False,
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        title_font_size=20
                    )
                    st.plotly_chart(fig_est, use_container_width=True)

                    mostrar_botiquin_emocional(df_est)

                    df_est_mostrar = preparar_tabla_registros(df_est)
                    st.dataframe(df_est_mostrar, use_container_width=True, hide_index=True)

                    excel_est = convertir_a_excel(df_est_mostrar, "Reporte_Mensual")
                    st.download_button(
                        label="📥 Descargar reporte mensual en Excel",
                        data=excel_est,
                        file_name=f"reporte_mensual_{year_est}_{month_est}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="descargar_reporte_mensual_estudiante"
                    )
                else:
                    st.info("No hay registros para ese mes con los filtros seleccionados.")

    elif pin != "":
        st.error("PIN incorrecto.")
