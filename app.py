import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MoodClass", page_icon="🎒", layout="centered")

# --- CONEXIÓN SEGURA ---
# Se prioriza el uso de Secrets para mayor seguridad
try:
    if "MONGO_URI" in st.secrets:
        uri = st.secrets["MONGO_URI"]
    else:
        uri = "mongodb+srv://joseycarito75_db_user:5jfbQjoh5B84RE4R@cluster0.hzl7cg0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
except:
    uri = "mongodb+srv://joseycarito75_db_user:5jfbQjoh5B84RE4R@cluster0.hzl7cg0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def get_database():
    client = MongoClient(uri)
    return client['moodclass_db']

db = get_database()
col_moods = db['moods']

# --- INTERFAZ ---
st.title("🎒 MoodClass")
tab1, tab2 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente"])

with tab1:
    with st.form("registro_emocion"):
        momento = st.selectbox("Momento", ["Entrada", "Salida"])
        emocion = st.selectbox("¿Cómo te sientes?", ["😊 Feliz", "😐 Normal", "😢 Triste", "😡 Molesto", "😴 Cansado"])
        if st.form_submit_button("Guardar Estado"):
            col_moods.insert_one({
                "day": str(date.today()), 
                "moment": momento, 
                "emotion": emocion,
                "timestamp": datetime.now()
            })
            st.success("¡Estado guardado!")

with tab2:
    pin = st.text_input("PIN Docente", type="password")
    if pin == "1234":
        datos = list(col_moods.find({"day": str(date.today())}))
        if datos:
            df = pd.DataFrame(datos)
            conteo = df['emotion'].value_counts().reset_index()
            conteo.columns = ['emocion', 'count']
            fig = px.bar(conteo, x="emocion", y="count", color="emocion", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay registros hoy.")
