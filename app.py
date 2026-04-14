# ======================================
# REPORTE POR ESTUDIANTE Y GRUPO
# ======================================
st.markdown('<div class="section-title">Reporte por estudiante y grupo completo</div>', unsafe_allow_html=True)

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

    # --------------------------------------
    # REPORTE POR DÍA
    # --------------------------------------
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

    # --------------------------------------
    # REPORTE POR MES
    # --------------------------------------
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
