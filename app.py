import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import predictor as ia

st.set_page_config(page_title="Asesor IA - Micronegocio", page_icon="📲", layout="centered")

if "configurado" not in st.session_state:
    st.session_state.configurado = False
    st.session_state.nombre = ""
    st.session_state.negocio = ""
    st.session_state.dia_actual = 1
    st.session_state.caja_efectivo = 500000
    st.session_state.cuentas_por_cobrar = 0
    st.session_state.cuentas_por_pagar_proveedores = 0
    st.session_state.inventario_acumulado = 1200000
    st.session_state.inventario_detalle = ""
    st.session_state.inventario_items = {}
    st.session_state.inventario_inicial_items = []
    st.session_state.clientes = {}
    st.session_state.clientes_iniciales = []
    st.session_state.proveedores = {}
    st.session_state.proveedores_iniciales = []
    st.session_state.deudas_iniciales = []
    st.session_state.cartera_inicial = 0
    st.session_state.bitacora_transacciones = []
    st.session_state.historial_interno = []
    st.session_state.alertas = []


def obtener_fecha_str():
    fecha_base = datetime(2026, 6, 1)
    return (fecha_base + timedelta(days=st.session_state.dia_actual - 1)).strftime("%d/%m/%Y")


def recalcular_cartera():
    st.session_state.cuentas_por_cobrar = sum(c["saldo"] for c in st.session_state.clientes.values())


def recalcular_proveedores():
    st.session_state.cuentas_por_pagar_proveedores = sum(p["saldo"] for p in st.session_state.proveedores.values())


def ajustar_inventario(rubro, cantidad, costo_unitario, tipo):
    if rubro not in st.session_state.inventario_items:
        st.session_state.inventario_items[rubro] = {"cantidad": 0, "costo_unitario": 0, "valor": 0}

    item = st.session_state.inventario_items[rubro]
    if tipo == "entrada":
        nueva_cantidad = item["cantidad"] + cantidad
        nuevo_valor = item["valor"] + (cantidad * costo_unitario)
        st.session_state.inventario_items[rubro] = {
            "cantidad": nueva_cantidad,
            "costo_unitario": nuevo_valor / nueva_cantidad if nueva_cantidad else 0,
            "valor": nuevo_valor,
        }
    elif tipo == "salida":
        if item["cantidad"] < cantidad:
            raise ValueError("Stock insuficiente")
        nueva_cantidad = item["cantidad"] - cantidad
        nuevo_valor = item["valor"] - (cantidad * item["costo_unitario"])
        st.session_state.inventario_items[rubro] = {
            "cantidad": nueva_cantidad,
            "costo_unitario": item["costo_unitario"],
            "valor": max(0, nuevo_valor),
        }

    st.session_state.inventario_acumulado = sum(i["valor"] for i in st.session_state.inventario_items.values())


def agregar_cliente_inicial(nombre, saldo, detalle):
    if not nombre:
        return
    st.session_state.clientes_iniciales.append({"cliente": nombre, "saldo": float(saldo), "detalle": detalle})


def agregar_proveedor_inicial(nombre, saldo, detalle):
    if not nombre:
        return
    st.session_state.proveedores_iniciales.append({"proveedor": nombre, "saldo": float(saldo), "detalle": detalle})


def agregar_item_inicial(nombre, cantidad, costo):
    if not nombre:
        return
    st.session_state.inventario_inicial_items.append({"articulo": nombre, "cantidad": int(cantidad), "costo_unitario": float(costo)})


def generar_alertas():
    alertas = []
    if st.session_state.caja_efectivo < 0:
        alertas.append("⚠️ La caja está negativa. Revisa los pagos inmediatos.")

    items_bajos = [r for r, d in st.session_state.inventario_items.items() if d["cantidad"] <= 3]
    if items_bajos:
        alertas.append(f"⚠️ Inventario bajo: {', '.join(items_bajos)}")

    for cliente, datos in st.session_state.clientes.items():
        if datos["saldo"] > 0:
            alertas.append(f"📌 Cliente {cliente} tiene saldo pendiente por cobrar.")

    for proveedor, datos in st.session_state.proveedores.items():
        if datos["saldo"] > 0:
            alertas.append(f"📌 Proveedor {proveedor} tiene saldo pendiente por pagar.")

    st.session_state.alertas = alertas


def flujo_caja_mensual():
    entradas = sum(item["monto"] for item in st.session_state.bitacora_transacciones if item["tipo"] in ["Venta Contado", "Venta Crédito", "Recaudo Cartera"])
    salidas = sum(item["monto"] for item in st.session_state.bitacora_transacciones if item["tipo"] in ["Compra Contado", "Compra Crédito", "Gasto Servicio público", "Gasto Nómina", "Gasto Arriendo"])
    return entradas - salidas


# ------------------------------------------------------------------------
# Utilidades para alimentar los modelos de Machine Learning con los datos
# reales que ya existen en la bitácora de la sesión actual.
# ------------------------------------------------------------------------
def _bitacora_df():
    if not st.session_state.bitacora_transacciones:
        return pd.DataFrame()
    return pd.DataFrame(st.session_state.bitacora_transacciones)


def calcular_promedios_recientes(dias=7):
    df = _bitacora_df()
    if df.empty:
        return 0.0, 0.0, 0.0

    fechas_recientes = df["fecha"].drop_duplicates().tolist()[-dias:]
    df_reciente = df[df["fecha"].isin(fechas_recientes)]
    n = max(len(fechas_recientes), 1)

    venta = df_reciente[df_reciente["tipo"].isin(["Venta Contado", "Venta Crédito"])]["monto"].sum()
    gasto = df_reciente[df_reciente["tipo"].str.contains("Gasto", na=False)]["monto"].sum()
    compra = df_reciente[df_reciente["tipo"].str.contains("Compra", na=False)]["monto"].sum()

    return venta / n, gasto / n, compra / n


def calcular_prop_credito_negocio():
    df = _bitacora_df()
    if df.empty:
        return 0.3
    contado = df[df["tipo"] == "Venta Contado"]["monto"].sum()
    credito = df[df["tipo"] == "Venta Crédito"]["monto"].sum()
    total = contado + credito
    return credito / total if total > 0 else 0.3


def perfil_riesgo_cliente(nombre_cliente):
    """Construye el perfil histórico del cliente a partir de sus fiados pasados."""
    df = _bitacora_df()
    if df.empty:
        return 0, 0, 0.0

    fiados = df[(df["tipo"] == "Venta Crédito") & (df["cliente"] == nombre_cliente)]
    pagos_totales_previos = len(fiados)
    if pagos_totales_previos == 0:
        return 0, 0, 0.0

    hoy = pd.to_datetime(obtener_fecha_str(), format="%d/%m/%Y")
    fiados_vencidos = fiados[pd.to_datetime(fiados["fecha_pago"]) < hoy]
    saldo_pendiente = st.session_state.clientes.get(nombre_cliente, {}).get("saldo", 0)
    pagos_tardios_previos = len(fiados_vencidos) if saldo_pendiente > 0 else max(0, len(fiados_vencidos) - 1)

    monto_promedio = fiados["monto"].mean()
    return pagos_tardios_previos, pagos_totales_previos, monto_promedio


def demanda_reciente_articulo(articulo, dias=7):
    df = _bitacora_df()
    if df.empty:
        return 0.0
    ventas_articulo = df[(df["articulo"] == articulo) & (df["tipo"].isin(["Venta Contado", "Venta Crédito"]))]
    fechas_recientes = df["fecha"].drop_duplicates().tolist()[-dias:]
    ventas_recientes = ventas_articulo[ventas_articulo["fecha"].isin(fechas_recientes)]
    return ventas_recientes["cantidad"].sum() / max(len(fechas_recientes), 1) if not ventas_recientes.empty else 0.0


if not st.session_state.configurado:
    st.title("📲 Instalación de tu Asesor Financiero")
    st.write("Configura el perfil de tu micronegocio para iniciar el cuaderno digital.")

    with st.form("form_instalacion", clear_on_submit=True):
        nombre_in = st.text_input("¿Cuál es tu nombre?", placeholder="Ej. Diana")
        negocio_in = st.text_input("¿Cómo se llama tu negocio?", placeholder="Ej. Tienda Caribe")
        caja_inicial = st.number_input("💵 Dinero en caja inicial ($):", min_value=0, step=1000, value=500000)

        st.subheader("📦 Inventario inicial por artículo")
        st.caption("Agrega uno por uno. Repite hasta terminar.")
        inv_articulo = st.text_input("Artículo", key="inv_articulo_temp")
        inv_cantidad = st.number_input("Cantidad", min_value=1, step=1, key="inv_cantidad_temp")
        inv_costo = st.number_input("Costo unitario ($)", min_value=0.0, step=100.0, key="inv_costo_temp")
        if st.form_submit_button("Agregar artículo al inventario inicial"):
            agregar_item_inicial(inv_articulo, inv_cantidad, inv_costo)
            st.success("Artículo agregado al inventario inicial.")

        if st.session_state.inventario_inicial_items:
            st.dataframe(pd.DataFrame(st.session_state.inventario_inicial_items), use_container_width=True)

        st.subheader("👥 Clientes iniciales")
        st.caption("Registra los clientes que ya tienen saldo por cobrar.")
        cli_nombre = st.text_input("Nombre del cliente", key="cli_nombre_temp")
        cli_saldo = st.number_input("Saldo inicial ($)", min_value=0.0, step=1000.0, key="cli_saldo_temp")
        cli_detalle = st.text_input("Detalle", key="cli_detalle_temp")
        if st.form_submit_button("Agregar cliente inicial"):
            agregar_cliente_inicial(cli_nombre, cli_saldo, cli_detalle)
            st.success("Cliente agregado.")

        if st.session_state.clientes_iniciales:
            st.dataframe(pd.DataFrame(st.session_state.clientes_iniciales), use_container_width=True)

        st.subheader("🏦 Proveedores iniciales")
        st.caption("Registra los proveedores que ya generan deuda por pagar.")
        prov_nombre = st.text_input("Nombre del proveedor", key="prov_nombre_temp")
        prov_saldo = st.number_input("Saldo inicial ($)", min_value=0.0, step=1000.0, key="prov_saldo_temp")
        prov_detalle = st.text_input("Detalle", key="prov_detalle_temp")
        if st.form_submit_button("Agregar proveedor inicial"):
            agregar_proveedor_inicial(prov_nombre, prov_saldo, prov_detalle)
            st.success("Proveedor agregado.")

        if st.session_state.proveedores_iniciales:
            st.dataframe(pd.DataFrame(st.session_state.proveedores_iniciales), use_container_width=True)

        if st.form_submit_button("Activar e Instalar App", type="primary"):
            if nombre_in and negocio_in:
                st.session_state.nombre = nombre_in.strip().capitalize()
                st.session_state.negocio = negocio_in.strip().upper()
                st.session_state.caja_efectivo = float(caja_inicial)
                st.session_state.inventario_items = {}
                for item in st.session_state.inventario_inicial_items:
                    st.session_state.inventario_items[item["articulo"]] = {
                        "cantidad": int(item["cantidad"]),
                        "costo_unitario": float(item["costo_unitario"]),
                        "valor": int(item["cantidad"]) * float(item["costo_unitario"]),
                    }
                st.session_state.inventario_acumulado = sum(i["valor"] for i in st.session_state.inventario_items.values())
                st.session_state.inventario_detalle = "; ".join(
                    f"{i['articulo']} x{i['cantidad']} @ ${i['costo_unitario']:,.0f}" for i in st.session_state.inventario_inicial_items
                )
                st.session_state.clientes = {}
                for item in st.session_state.clientes_iniciales:
                    st.session_state.clientes[item["cliente"]] = {"saldo": float(item["saldo"]), "detalle": item["detalle"]}
                st.session_state.proveedores = {}
                for item in st.session_state.proveedores_iniciales:
                    st.session_state.proveedores[item["proveedor"]] = {"saldo": float(item["saldo"]), "detalle": item["detalle"]}
                recalcular_cartera()
                recalcular_proveedores()
                st.session_state.cartera_inicial = st.session_state.cuentas_por_cobrar
                st.session_state.configurado = True
                st.rerun()
            else:
                st.error("Por favor completa ambos campos para continuar.")

else:
    st.title(f"🏢 {st.session_state.negocio}")
    st.subheader(f"👋 ¡Ajá, {st.session_state.nombre}! Bienvenido al Día {st.session_state.dia_actual}")

    col_caja, col_cart = st.columns(2)
    col_caja.metric("💵 Efectivo en Caja", f"${st.session_state.caja_efectivo:,}")
    col_cart.metric("💸 Cuentas por Cobrar", f"${st.session_state.cuentas_por_cobrar:,}")

    st.info(f"📅 **Fecha del Calendario:** {obtener_fecha_str()}")

    recalcular_cartera()
    recalcular_proveedores()
    generar_alertas()

    st.caption(f"💳 Saldo inicial de cartera: ${st.session_state.cartera_inicial:,.0f}")
    st.caption(f"🏦 Saldo inicial de proveedores: ${st.session_state.cuentas_por_pagar_proveedores:,.0f}")

    if st.session_state.inventario_detalle:
        st.caption(f"📦 Inventario inicial detallado: {st.session_state.inventario_detalle}")

    if st.session_state.inventario_items:
        st.write("### 📦 Inventario actual")
        inv_df = pd.DataFrame([
            {"Artículo": rubro, "Cantidad": datos["cantidad"], "Costo Unitario": datos["costo_unitario"], "Valor": datos["valor"]}
            for rubro, datos in st.session_state.inventario_items.items()
        ])
        st.dataframe(inv_df, use_container_width=True)

    if st.session_state.clientes:
        st.write("### 👥 Saldos por cliente")
        clientes_df = pd.DataFrame([
            {"Cliente": nombre, "Saldo": datos["saldo"], "Detalle": datos["detalle"]}
            for nombre, datos in st.session_state.clientes.items()
        ])
        st.dataframe(clientes_df, use_container_width=True)

    if st.session_state.proveedores:
        st.write("### 🏦 Saldos por proveedor")
        prov_df = pd.DataFrame([
            {"Proveedor": nombre, "Saldo": datos["saldo"], "Detalle": datos["detalle"]}
            for nombre, datos in st.session_state.proveedores.items()
        ])
        st.dataframe(prov_df, use_container_width=True)

    if st.session_state.alertas:
        st.write("### 🚨 Alertas de flujo de caja")
        for alerta in st.session_state.alertas:
            st.warning(alerta)

    st.markdown("---")
    st.write("## 🤖 Predicciones con Inteligencia Artificial")
    st.caption(
        "Estos 4 modelos fueron entrenados con datos sintéticos que imitan el "
        "comportamiento de micronegocios tipo tienda de barrio. Sirven como línea "
        "base predictiva; se recomienda re-entrenarlos con datos reales más adelante."
    )

    if not ia.modelos_disponibles():
        st.error("No se encontraron los modelos entrenados en la carpeta /modelos.")
    else:
        tab_flujo, tab_riesgo, tab_demanda, tab_ccc = st.tabs([
            "💵 Flujo de Caja", "⚠️ Riesgo de Mora", "📦 Demanda Inventario", "🔄 CCC Proyectado"
        ])

        # 1) FLUJO DE CAJA -------------------------------------------------
        with tab_flujo:
            prom_venta_7d, prom_gasto_7d, prom_compra_7d = calcular_promedios_recientes(7)
            fecha_dt = pd.to_datetime(obtener_fecha_str(), format="%d/%m/%Y")

            venta_hoy = sum(r["monto"] for r in st.session_state.bitacora_transacciones
                             if r["fecha"] == obtener_fecha_str() and r["tipo"] == "Venta Contado")
            credito_hoy = sum(r["monto"] for r in st.session_state.bitacora_transacciones
                               if r["fecha"] == obtener_fecha_str() and r["tipo"] == "Venta Crédito")

            flujo_pred = ia.predecir_flujo_caja(
                dia_semana=fecha_dt.dayofweek,
                caja=st.session_state.caja_efectivo,
                venta_contado_hoy=venta_hoy,
                venta_credito_hoy=credito_hoy,
                prom_venta_7d=prom_venta_7d,
                prom_gasto_7d=prom_gasto_7d,
                prom_compra_7d=prom_compra_7d,
                cartera_actual=st.session_state.cuentas_por_cobrar,
                inventario_valor=st.session_state.inventario_acumulado,
            )
            st.metric("Flujo de caja neto estimado (próximos 7 días)", f"${flujo_pred:,.0f}")
            if flujo_pred < 0:
                st.warning("💡 El modelo anticipa un flujo de caja negativo la próxima semana. Considera acelerar el recaudo de cartera o posponer compras no urgentes.")
            else:
                st.success("💡 El modelo anticipa un flujo de caja positivo para la próxima semana.")

        # 2) RIESGO DE MORA POR CLIENTE ------------------------------------
        with tab_riesgo:
            clientes_con_saldo = {c: d for c, d in st.session_state.clientes.items() if d["saldo"] > 0}
            if not clientes_con_saldo:
                st.info("No hay clientes con saldo pendiente por evaluar.")
            else:
                prop_credito = calcular_prop_credito_negocio()
                filas = []
                for cliente, datos in clientes_con_saldo.items():
                    tardios, totales, monto_prom = perfil_riesgo_cliente(cliente)
                    riesgo = ia.predecir_riesgo_cliente(
                        monto_credito=datos["saldo"],
                        plazo_dias=15,
                        pagos_tardios_previos=tardios,
                        pagos_totales_previos=totales,
                        monto_promedio_cliente=monto_prom if monto_prom else datos["saldo"],
                        prop_credito_negocio=prop_credito,
                    )
                    filas.append({"Cliente": cliente, "Saldo": datos["saldo"], "Riesgo de mora": f"{riesgo:.0%}"})

                df_riesgo = pd.DataFrame(filas).sort_values("Riesgo de mora", ascending=False)
                st.dataframe(df_riesgo, use_container_width=True)
                st.caption("El riesgo se calcula con base en el historial de fiados de cada cliente dentro de esta sesión. Con pocos registros, la estimación es preliminar.")

        # 3) DEMANDA DE INVENTARIO -----------------------------------------
        with tab_demanda:
            if not st.session_state.inventario_items:
                st.info("Aún no hay artículos en inventario para proyectar demanda.")
            else:
                fecha_dt = pd.to_datetime(obtener_fecha_str(), format="%d/%m/%Y")
                filas = []
                for articulo, datos in st.session_state.inventario_items.items():
                    prom_demanda = demanda_reciente_articulo(articulo, 7)
                    demanda_pred = ia.predecir_demanda_articulo(
                        articulo=articulo,
                        dia_semana=fecha_dt.dayofweek,
                        stock_actual=datos["cantidad"],
                        prom_demanda_7d=prom_demanda,
                    )
                    faltante = max(0, demanda_pred - datos["cantidad"])
                    filas.append({
                        "Artículo": articulo,
                        "Stock actual": round(datos["cantidad"], 1),
                        "Demanda estimada (7 días)": round(demanda_pred, 1),
                        "Sugerencia de compra": round(faltante, 1),
                    })
                df_demanda = pd.DataFrame(filas)
                st.dataframe(df_demanda, use_container_width=True)

                articulos_criticos = df_demanda[df_demanda["Sugerencia de compra"] > 0]
                if not articulos_criticos.empty:
                    st.warning("💡 Considera reabastecer: " + ", ".join(articulos_criticos["Artículo"].tolist()))

        # 4) CCC PROYECTADO --------------------------------------------------
        with tab_ccc:
            dpo_estimado = st.slider(
                "Días promedio que te toma pagarle a tus proveedores (DPO estimado):",
                min_value=5, max_value=45, value=20,
                help="Esta app aún no lleva el historial detallado de plazos pactados con cada proveedor, así que este valor se ingresa manualmente.",
            )
            prom_venta_15d, _, _ = calcular_promedios_recientes(15)
            ventas_15d = prom_venta_15d * 15
            costo_ventas_15d = ventas_15d * 0.65

            if ventas_15d <= 0:
                st.info("Registra algunos movimientos primero para poder proyectar el CCC.")
            else:
                dso, dio, ccc_actual = ia.calcular_dso_dio_dpo(
                    cartera_actual=st.session_state.cuentas_por_cobrar,
                    inventario_valor=st.session_state.inventario_acumulado,
                    ventas_recientes=ventas_15d,
                    costo_ventas_recientes=costo_ventas_15d,
                    dpo_estimado=dpo_estimado,
                )
                ccc_proyectado = ia.predecir_ccc(
                    dso=dso, dio=dio, dpo=dpo_estimado,
                    cartera_actual=st.session_state.cuentas_por_cobrar,
                    inventario_valor=st.session_state.inventario_acumulado,
                    prom_venta_15d=prom_venta_15d,
                )

                col1, col2, col3 = st.columns(3)
                col1.metric("DSO (días en cobrar)", f"{dso:.1f}")
                col2.metric("DIO (días en inventario)", f"{dio:.1f}")
                col3.metric("DPO (días en pagar)", f"{dpo_estimado:.1f}")

                st.metric("🔄 CCC actual", f"{ccc_actual:.1f} días")
                st.metric("🔮 CCC proyectado (próximos 15 días)", f"{ccc_proyectado:.1f} días")

                if ccc_proyectado > ccc_actual:
                    st.warning("💡 El modelo anticipa que tu dinero tardará más días en volver a caja. Vale la pena revisar plazos de fiado o rotación de inventario.")
                else:
                    st.success("💡 El modelo anticipa una mejora (o estabilidad) en la velocidad con la que tu dinero vuelve a caja.")

    st.markdown("---")
    st.write("### 📝 ¿Qué movimiento deseas registrar hoy?")

    opcion = st.selectbox("Selecciona el tipo de operación:", [
        "Venta de Contado",
        "Venta a Crédito (Fíado)",
        "Recaudo (Cliente paga deuda)",
        "Compra de Mercancía/Insumos",
        "Gastos (Servicios, Nómina, Arriendo)"
    ])

    with st.form("formulario_registro", clear_on_submit=True):
        if opcion == "Venta de Contado":
            cliente = st.text_input("Nombre del Cliente (opcional):")
            articulo = st.text_input("Artículo vendido:")
            cantidad = st.number_input("Cantidad vendida:", min_value=1, step=1)
            precio_unitario = st.number_input("Precio unitario ($):", min_value=0, step=100)
            detalle = st.text_input("Detalle adicional:")
            monto = cantidad * precio_unitario
            st.write(f"💰 Total estimado de la venta: ${monto:,.0f}")

            if st.form_submit_button("Guardar Venta Contado"):
                try:
                    ajustar_inventario(articulo, cantidad, precio_unitario, "salida")
                except ValueError as e:
                    st.error(str(e))
                    st.stop()
                st.session_state.caja_efectivo += monto
                reg = {
                    "fecha": obtener_fecha_str(),
                    "tipo": "Venta Contado",
                    "monto": monto,
                    "articulo": articulo,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "cliente": cliente,
                    "detalle": detalle or f"Venta de {articulo}",
                }
                st.session_state.bitacora_transacciones.append(reg)
                st.session_state.historial_interno.append(("venta_contado", reg))
                st.success("✔ Venta de contado guardada.")
                st.rerun()

        elif opcion == "Venta a Crédito (Fíado)":
            cliente = st.text_input("Nombre del Cliente:")
            articulo = st.text_input("Artículo fiado:")
            cantidad = st.number_input("Cantidad:", min_value=1, step=1)
            precio_unitario = st.number_input("Precio unitario ($):", min_value=0, step=100)
            detalle = st.text_input("Detalle adicional:")
            fecha_pago = st.date_input("Fecha probable de pago", value=datetime.now().date() + timedelta(days=15))
            enviar_whatsapp = st.checkbox("¿Desea enviar un cobro por WhatsApp al vencimiento?")
            monto = cantidad * precio_unitario
            st.write(f"💰 Total estimado del fiado: ${monto:,.0f}")

            if st.form_submit_button("Guardar Fíado"):
                try:
                    ajustar_inventario(articulo, cantidad, precio_unitario, "salida")
                except ValueError as e:
                    st.error(str(e))
                    st.stop()
                if cliente:
                    if cliente not in st.session_state.clientes:
                        st.session_state.clientes[cliente] = {"saldo": 0, "detalle": ""}
                    st.session_state.clientes[cliente]["saldo"] += monto
                    st.session_state.clientes[cliente]["detalle"] = st.session_state.clientes[cliente]["detalle"] or f"Venta a crédito de {articulo}"
                    recalcular_cartera()
                reg = {
                    "fecha": obtener_fecha_str(),
                    "tipo": "Venta Crédito",
                    "monto": monto,
                    "articulo": articulo,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "cliente": cliente,
                    "detalle": detalle or f"Fiado de {articulo}",
                    "fecha_pago": fecha_pago.strftime("%Y-%m-%d"),
                    "enviar_whatsapp": enviar_whatsapp,
                }
                st.session_state.bitacora_transacciones.append(reg)
                st.session_state.historial_interno.append(("venta_credito", reg))
                st.success(f"✔ Fíado anotado a nombre de {cliente}.")
                st.rerun()

        elif opcion == "Recaudo (Cliente paga deuda)":
            cliente = st.text_input("Nombre del Cliente que paga:")
            monto = st.number_input("Monto que abona o paga ($):", min_value=0, step=1000)
            detalle = st.text_input("Detalle del recaudo:")

            if st.form_submit_button("Registrar Recaudo"):
                st.session_state.caja_efectivo += monto
                if cliente and cliente in st.session_state.clientes:
                    st.session_state.clientes[cliente]["saldo"] = max(0, st.session_state.clientes[cliente]["saldo"] - monto)
                    st.session_state.clientes[cliente]["detalle"] = st.session_state.clientes[cliente]["detalle"] or "Pago parcial"
                    recalcular_cartera()
                else:
                    st.session_state.cuentas_por_cobrar = max(0, st.session_state.cuentas_por_cobrar - monto)
                reg = {
                    "fecha": obtener_fecha_str(),
                    "tipo": "Recaudo Cartera",
                    "monto": monto,
                    "cliente": cliente,
                    "detalle": detalle or f"Cliente {cliente} pagó deuda",
                }
                st.session_state.bitacora_transacciones.append(reg)
                st.session_state.historial_interno.append(("recaudo", reg))
                st.success("✔ Recaudo inyectado a caja.")
                st.rerun()

        elif opcion == "Compra de Mercancía/Insumos":
            proveedor = st.text_input("Nombre del Proveedor:")
            tipo_pago = st.radio("Método de Pago:", ["Contado", "Crédito"])
            articulo = st.text_input("Artículo / mercancía ingresada:")
            cantidad = st.number_input("Cantidad ingresada:", min_value=1, step=1)
            costo_unitario = st.number_input("Costo unitario ($):", min_value=0, step=100)
            detalle = st.text_input("Detalle adicional:")
            fecha_vencimiento = st.date_input("Fecha probable de vencimiento", value=datetime.now().date() + timedelta(days=15))
            monto = cantidad * costo_unitario
            st.write(f"💰 Total estimado del ingreso: ${monto:,.0f}")

            if st.form_submit_button("Guardar Compra"):
                ajustar_inventario(articulo, cantidad, costo_unitario, "entrada")
                if tipo_pago == "Contado":
                    st.session_state.caja_efectivo -= monto
                else:
                    if proveedor not in st.session_state.proveedores:
                        st.session_state.proveedores[proveedor] = {"saldo": 0, "detalle": ""}
                    st.session_state.proveedores[proveedor]["saldo"] += monto
                    st.session_state.proveedores[proveedor]["detalle"] = st.session_state.proveedores[proveedor]["detalle"] or f"Compra de {articulo}"
                    recalcular_proveedores()
                reg = {
                    "fecha": obtener_fecha_str(),
                    "tipo": f"Compra {tipo_pago}",
                    "monto": monto,
                    "articulo": articulo,
                    "cantidad": cantidad,
                    "costo_unitario": costo_unitario,
                    "proveedor": proveedor,
                    "detalle": detalle or f"Ingreso de {articulo}",
                    "fecha_vencimiento": fecha_vencimiento.strftime("%Y-%m-%d"),
                }
                st.session_state.bitacora_transacciones.append(reg)
                st.session_state.historial_interno.append(("compra_mercancia", reg))
                st.success("✔ Compra cargada al stock.")
                st.rerun()

        elif opcion == "Gastos (Servicios, Nómina, Arriendo)":
            tipo_gasto = st.selectbox("Tipo de Gasto:", ["Servicio público", "Nómina", "Arriendo"])
            monto = st.number_input("Monto del gasto ($):", min_value=0, step=1000)
            recurrente = st.checkbox("¿Es un pago recurrente?")
            periodicidad = st.selectbox("Periodicidad", ["Única", "Semanal", "Mensual", "Anual"], disabled=not recurrente)
            fecha_pago = st.date_input("Fecha probable de pago", value=datetime.now().date() + timedelta(days=15))
            observacion = st.text_input("Observaciones / Notas de control:", placeholder="Ej. Pago recibo de luz Air-e, tarifa alta")

            if st.form_submit_button("Guardar Gasto"):
                st.session_state.caja_efectivo -= monto
                reg = {
                    "fecha": obtener_fecha_str(),
                    "tipo": f"Gasto {tipo_gasto}",
                    "monto": monto,
                    "detalle": f"Nota: {observacion}",
                    "recurrente": recurrente,
                    "periodicidad": periodicidad if recurrente else "Única",
                    "fecha_pago": fecha_pago.strftime("%Y-%m-%d"),
                }
                st.session_state.bitacora_transacciones.append(reg)
                st.session_state.historial_interno.append(("gasto", reg))
                st.success(f"✔ Gasto de {tipo_gasto} registrado.")
                st.rerun()

    st.markdown("---")
    col_av, col_corr, col_mes = st.columns(3)

    if col_av.button("⏩ Avanzar Día", use_container_width=True):
        if st.session_state.dia_actual < 30:
            st.session_state.dia_actual += 1
            st.rerun()

    if col_corr.button("✏️ Corregir Último", use_container_width=True, type="secondary"):
        if st.session_state.historial_interno:
            tipo_raiz, ultimo_reg = st.session_state.historial_interno.pop()
            st.session_state.bitacora_transacciones.remove(ultimo_reg)

            if tipo_raiz == "venta_contado":
                st.session_state.caja_efectivo -= ultimo_reg["monto"]
                if ultimo_reg.get("articulo"):
                    ajustar_inventario(ultimo_reg["articulo"], ultimo_reg["cantidad"], ultimo_reg["precio_unitario"], "entrada")
            elif tipo_raiz == "venta_credito":
                st.session_state.caja_efectivo -= 0
                if ultimo_reg.get("articulo"):
                    ajustar_inventario(ultimo_reg["articulo"], ultimo_reg["cantidad"], ultimo_reg["precio_unitario"], "entrada")
                cliente = ultimo_reg.get("cliente", "")
                if cliente and cliente in st.session_state.clientes:
                    st.session_state.clientes[cliente]["saldo"] = max(0, st.session_state.clientes[cliente]["saldo"] - ultimo_reg["monto"])
                recalcular_cartera()
            elif tipo_raiz == "recaudo":
                st.session_state.caja_efectivo -= ultimo_reg["monto"]
                cliente = ultimo_reg.get("cliente", "")
                if cliente and cliente in st.session_state.clientes:
                    st.session_state.clientes[cliente]["saldo"] += ultimo_reg["monto"]
                recalcular_cartera()
            elif tipo_raiz == "compra_mercancia":
                if ultimo_reg.get("articulo"):
                    ajustar_inventario(ultimo_reg["articulo"], ultimo_reg["cantidad"], ultimo_reg["costo_unitario"], "salida")
                if "Contado" in ultimo_reg["tipo"]:
                    st.session_state.caja_efectivo += ultimo_reg["monto"]
                else:
                    proveedor = ultimo_reg.get("proveedor", "")
                    if proveedor and proveedor in st.session_state.proveedores:
                        st.session_state.proveedores[proveedor]["saldo"] = max(0, st.session_state.proveedores[proveedor]["saldo"] - ultimo_reg["monto"])
                    recalcular_proveedores()
            elif tipo_raiz == "gasto":
                st.session_state.caja_efectivo += ultimo_reg["monto"]

            st.warning("🔄 Último movimiento anulado y saldos corregidos.")
            st.rerun()
        else:
            st.error("No hay registros en este ciclo para deshacer.")

    if col_mes.button("📊 Balance Mensual", use_container_width=True, type="primary"):
        st.session_state.dia_actual = 30

    if st.session_state.bitacora_transacciones:
        st.write("### 📝 Bitácora de Registros Recientes")
        df_logs = pd.DataFrame(st.session_state.bitacora_transacciones)
        st.dataframe(df_logs.tail(5), use_container_width=True)

    st.write("### 📉 Flujo de caja mensual estimado")
    st.metric("Flujo de caja del mes", f"${flujo_caja_mensual():,.0f}")

    st.write("### 📊 Informe detallado")
    informe_df = pd.DataFrame(st.session_state.bitacora_transacciones)
    if not informe_df.empty:
        st.dataframe(informe_df, use_container_width=True)
    else:
        st.info("Aún no hay movimientos para reportar.")

    if st.session_state.dia_actual >= 30:
        st.markdown("---")
        st.header("📋 Cuadro de Mandos y Auditoría de Cierre")

        df_total = pd.DataFrame(st.session_state.bitacora_transacciones) if st.session_state.bitacora_transacciones else pd.DataFrame()

        v_contado = sum(d["monto"] for d in st.session_state.bitacora_transacciones if d["tipo"] == "Venta Contado")
        v_credito = sum(d["monto"] for d in st.session_state.bitacora_transacciones if d["tipo"] == "Venta Crédito")
        g_totales = sum(d["monto"] for d in st.session_state.bitacora_transacciones if "Gasto" in d["tipo"])
        c_totales = sum(d["monto"] for d in st.session_state.bitacora_transacciones if "Compra" in d["tipo"])

        ventas_mes = v_contado + v_credito
        costo_mercancia = c_totales * 0.65
        utilidad_neta = (ventas_mes - costo_mercancia) - g_totales

        tab1, tab2, tab3 = st.tabs(["📊 Rentabilidad", "🏛️ Situación Patrimonial", "🎯 Indicadores Traducidos"])

        with tab1:
            st.write("### Estado de Resultados Simplificado")
            st.write(f"**(+) Ventas Totales del Periodo:** ${ventas_mes:,}")
            st.write(f"**(-) Costo Estimado de Mercancía:** ${costo_mercancia:,}")
            st.write(f"**(-) Gastos Operativos de Administración:** ${g_totales:,}")
            st.write(f"## Utilidad Neta del Mes: ${utilidad_neta:,}")

        with tab2:
            st.write("### Estado de Situación Financiera (Balance General)")
            st.write(f"**• Caja y Disponible:** ${st.session_state.caja_efectivo:,}")
            st.write(f"**• Cartera por Cobrar:** ${st.session_state.cuentas_por_cobrar:,}")
            st.write(f"**• Inventarios en Stock:** ${st.session_state.inventario_acumulado:,}")
            st.write(f"**• Pasivos (Proveedores):** ${st.session_state.cuentas_por_pagar_proveedores:,}")
            st.write(f"## Patrimonio Neto Real: ${(st.session_state.caja_efectivo + st.session_state.cuentas_por_cobrar + st.session_state.inventario_acumulado) - st.session_state.cuentas_por_pagar_proveedores:,}")

        with tab3:
            st.write("### Asesoría Inclusiva de la IA")
            ktno = st.session_state.inventario_acumulado + st.session_state.cuentas_por_cobrar
            st.metric("🔸 Capital de Trabajo Operativo (KTNO)", f"${ktno:,}", help="Dinero atrapado en el negocio")
            st.write("> **Traducción de la IA:** Este valor representa la riqueza que tienes congelada en tus estantes y en la calle ('fíados'). Es el motor que necesitas para abrir tu cortina comercial el próximo mes.")

            if utilidad_neta > 0 and st.session_state.caja_efectivo < v_credito:
                st.warning(f"💡 **Recomendación Estratégica:** ¡Ojo, {st.session_state.nombre}! Tu negocio muestra ganancias sobre el papel, pero tu caja real está baja. Tu dinero está atrapado en la calle. El próximo mes enfócate en el recaudo y ponle un freno a los fíados.")
            else:
                st.success(f"💡 **Recomendación Estratégica:** Mantienes un equilibrio óptimo entre tus utilidades y el dinero en efectivo. Sigue cuidando tu flujo de caja de la misma forma.")

        st.write("### 🔍 Auditoría de Saldos y Desglose Analítico")
        col_aud_c, col_aud_g = st.columns(2)

        if col_aud_c.button("🔎 Desglosar Clientes Deudores"):
            if not df_total.empty:
                df_cart = df_total[df_total["tipo"] == "Venta Crédito"]
                st.dataframe(df_cart[["fecha", "detalle", "monto"]], use_container_width=True)
            else:
                st.write("No hay deudas este mes.")

        if col_aud_g.button("🔎 Desglosar Observaciones de Gastos"):
            if not df_total.empty:
                df_gas = df_total[df_total["tipo"].str.contains("Gasto", na=False)]
                st.dataframe(df_gas[["fecha", "tipo", "detalle", "monto"]], use_container_width=True)
            else:
                st.write("No hay gastos este mes.")

        if st.button("🔙 Reiniciar Ciclo y Volver al Flujo Diario", type="primary"):
            st.session_state.dia_actual = 1
            st.rerun()
