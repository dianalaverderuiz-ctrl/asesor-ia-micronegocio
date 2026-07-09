import streamlit as st
import pandas as pd
from datetime import datetime, date

# Configuración inicial del entorno de analítica
st.set_page_config(page_title="Asesor IA - Finanzas de Micronegocios", layout="wide")

# --- CENTRAL DE PERSISTENCIA CONTABLE (session_state) ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'db_inventario' not in st.session_state:
    st.session_state.db_inventario = {}  # { "Producto": {"cantidad": X, "costo_u": Y, "ventas_unidades": Z} }
if 'db_clientes' not in st.session_state:
    st.session_state.db_clientes = {}     # { "Cliente": saldo_inicial }
if 'db_proveedores' not in st.session_state:
    st.session_state.db_proveedores = {} # { "Proveedor": saldo_inicial }
if 'libro_diario' not in st.session_state:
    st.session_state.libro_diario = []
if 'caja_inicial' not in st.session_state:
    st.session_state.caja_inicial = 0.0

# Estilos CSS de la interfaz ejecutiva
st.markdown("""
    <style>
    .stButton>button { width: 100%; font-weight: bold; }
    .kpi-box { background-color: #f8f9fa; border-left: 5px solid #1c3d5a; padding: 15px; border-radius: 4px; }
    .alert-warn { background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 12px; border-radius: 4px; margin-bottom: 8px; }
    </style>
""", unsafe_allow_html=True)

# =========================================================================
# FASE 1: PRE-CARGA E INGESTA COMPLETA DE SALDOS INICIALES
# =========================================================================
if st.session_state.step == 1:
    st.title("🏛️ Balance de Apertura e Ingesta de Saldos Iniciales")
    st.markdown("Configure de forma analítica el estado inicial de su micronegocio antes de inicializar el diario.")
    
    col_e1, col_e2 = st.columns(2)
    nombre_e = col_e1.text_input("Nombre del Empresario:", "Diana Laverde")
    negocio = col_e2.text_input("Razón Comercial del Micronegocio:", "Mi Micronegocio")
    caja_inv = st.number_input("Efectivo Inicial en Caja / Bancos ($ COP):", min_value=0.0, value=500000.0, step=50000.0)

    st.markdown("---")
    
    # 1. Componente de Inventario Inicial
    st.subheader("📦 1. Cargar Productos al Inventario de Apertura")
    c_inv1, c_inv2, c_inv3 = st.columns([2, 1, 1])
    p_nombre = c_inv1.text_input("Nombre del Producto / Artículo:")
    p_cant = c_inv2.number_input("Cantidad Disponible:", min_value=0, value=0)
    p_costo = c_inv3.number_input("Costo Unitario ($ COP):", min_value=0.0, value=0.0)
    if st.button("➕ Registrar Producto en Inventario Inicial"):
        if p_nombre and p_cant > 0:
            st.session_state.db_inventario[p_nombre] = {"cantidad": p_cant, "costo_u": p_costo, "ventas_unidades": 0}
            st.success(f"Producto '{p_nombre}' añadido al inventario inicial.")
    if st.session_state.db_inventario:
        st.write("**Inventario Cargado Histórico:**")
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_inventario, orient='index'))

    st.markdown("---")
    
    # 2. Componente de Cartera Inicial
    st.subheader("👥 2. Cargar Cartera de Clientes (Saldos por Cobrar)")
    c_cl1, c_cl2 = st.columns(2)
    cl_nombre = c_cl1.text_input("Nombre del Cliente:")
    cl_saldo = c_cl2.number_input("Saldo Pendiente que Trae ($ COP):", min_value=0.0, value=0.0)
    if st.button("➕ Registrar Cliente en Cartera"):
        if cl_nombre and cl_saldo > 0:
            st.session_state.db_clientes[cl_nombre] = cl_saldo
            st.success(f"Cliente '{cl_nombre}' indexado con saldo inicial.")
    if st.session_state.db_clientes:
        st.write("**Cartera de Apertura:**")
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_clientes, orient='index', columns=['Saldo Inicial']))

    st.markdown("---")
    
    # 3. Componente de Proveedores Iniciales
    st.subheader("🏭 3. Cargar Cuentas por Pagar (Proveedores Históricos)")
    c_pr1, c_pr2 = st.columns(2)
    pr_nombre = c_pr1.text_input("Nombre del Proveedor:")
    pr_saldo = c_pr2.number_input("Saldo de la Deuda Pendiente ($ COP):", min_value=0.0, value=0.0)
    if st.button("➕ Registrar Cuenta por Pagar"):
        if pr_nombre and pr_saldo > 0:
            st.session_state.db_proveedores[pr_nombre] = pr_saldo
            st.success(f"Proveedor '{pr_nombre}' indexado con saldo inicial.")
    if st.session_state.db_proveedores:
        st.write("**Cuentas por Pagar de Apertura:**")
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_proveedores, orient='index', columns=['Saldo por Pagar']))

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚀 CONSOLIDAR BALANCE DE APERTURA Y ACTIVAR ASESOR", type="primary"):
        st.session_state.nombre_e = nombre_e
        st.session_state.negocio = negocio
        st.session_state.caja_inicial = caja_inv
        st.session_state.step = 2
        st.rerun()

# =========================================================================
# FASE 2: MOTOR DE EJECUCIÓN, CUATRO FRENTES Y ASESOR FINANCIERO
# =========================================================================
else:
    # Recalcular saldos dinámicos basados en la apertura y el libro diario
    val_inv_apertura = sum(v["cantidad"] * v["costo_u"] for v in st.session_state.db_inventario.values())
    val_cartera_apertura = sum(st.session_state.db_clientes.values())
    val_proveedores_apertura = sum(st.session_state.db_proveedores.values())
    
    caja_actual = st.session_state.caja_inicial
    cartera_actual = val_cartera_apertura
    proveedores_actual = val_proveedores_apertura

    # Procesar transacciones asentadas para actualizar saldos en tiempo real
    for trans in st.session_state.libro_diario:
        total = trans["Total"]
        modo = trans["Modo"]
        frente = trans["Frente"]
        
        if frente == "COMPRA":
            if modo == "Contado": caja_actual -= total
            else: proveedores_actual += total
        elif frente == "VENTA":
            if modo == "Contado": caja_actual += total
            else: cartera_actual += total
        elif frente == "GASTO":
            caja_actual -= total
        elif frente == "COBRO":
            caja_actual += total
            cartera_actual -= total
        elif frente == "PAGO":
            caja_actual -= total
            proveedores_actual -= total

    # Interfaz de Usuario Central
    st.title(f"📊 Panel Financiero Integral: {st.session_state.negocio}")
    st.caption(f"Responsable Técnico: {st.session_state.nombre_e} | Libro Diario e Inteligencia Financiera")
    
    # KPIs Superiores de Control de Saldos
    st.subheader("📈 Monitoreo de Saldos de Trabajo en Tiempo Real")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("💵 DISPONIBLE EN CAJA", f"${caja_actual:,.2f} COP")
    kpi2.metric("👥 TOTAL CARTERA DE CLIENTES", f"${cartera_actual:,.2f} COP")
    kpi3.metric("🏭 PASIVOS TOTALES (PROVEEDORES)", f"${proveedores_actual:,.2f} COP")
    
    st.markdown("---")
    
    # --- INTERFAZ TÁCTIL DE LOS CUATRO FRENTES Y GASTOS ---
    st.subheader("⚡ Acciones del Ciclo Operativo")
    f1, f2, f3, f4, f5 = st.columns(5)
    if f1.button("🛒 COMPRAS (Proveedores/Inventario)"): st.session_state.frente = "COMPRA"
    if f2.button("💰 VENTAS (Clientes/Inventario)"): st.session_state.frente = "VENTA"
    if f3.button("💸 GASTOS (Servicios/Nómina/Arriendo)"): st.session_state.frente = "GASTO"
    if f4.button("📥 COBROS (Recaudo de Cartera)"): st.session_state.frente = "COBRO"
    if f5.button("🏦 PAGOS (Abonos a Proveedores)"): st.session_state.frente = "PAGO"

    # Formularios de Asentamiento Transaccional
    if 'frente' in st.session_state:
        st.markdown(f"### ✏️ Nuevo Registro Contable: {st.session_state.frente}")
        with st.form("registro_operativo"):
            fecha_op = st.date_input("Fecha contable:", date.today())
            
            if st.session_state.frente == "COMPRA":
                prov_sel = st.text_input("Nombre del Proveedor:")
                prod_compra = st.text_input("Producto/Artículo a ingresar:")
                cant_c = st.number_input("Cantidad Comprada:", min_value=1, value=1)
                costo_c = st.number_input("Costo Unitario ($ COP):", min_value=0.0)
                modo_pago = st.radio("Método de Adquisición:", ["Contado", "Crédito"])
                vence_op = st.date_input("Fecha Límite de Pago de la Obligación:", date.today())
                
            elif st.session_state.frente == "VENTA":
                # Validar si existen clientes e inventarios
                list_cl = list(st.session_state.db_clientes.keys()) if st.session_state.db_clientes else ["Cliente General"]
                list_pr = list(st.session_state.db_inventario.keys()) if st.session_state.db_inventario else ["Producto General"]
                
                cl_sel = st.selectbox("Seleccionar Cliente:", list_cl)
                prod_venta = st.selectbox("Seleccionar Artículo del Inventario:", list_pr)
                cant_v = st.number_input("Cantidad Vendida:", min_value=1, value=1)
                precio_v = st.number_input("Precio Unitario de Venta ($ COP):", min_value=0.0)
                modo_pago = st.radio("Condición Comercial de la Venta:", ["Contado", "Crédito"])
                vence_op = st.date_input("Fecha Límite de Recaudo de Cartera:", date.today())
                
            elif st.session_state.frente == "GASTO":
                tipo_g = st.selectbox("Categoría del Gasto:", ["Servicio Público", "Nómina", "Arriendo"])
                detalle_g = "N/A"
                if tipo_g == "Servicio Público":
                    detalle_g = st.selectbox("Detalle de la Factura:", ["Agua", "Luz", "Gas"])
                valor_g = st.number_input("Monto Total del Gasto ($ COP):", min_value=0.0)
                vence_op = st.date_input("Próxima fecha posible de pago / Vencimiento de Factura:", date.today())
                modo_pago = "Contado"

            elif st.session_state.frente == "COBRO":
                cl_list = list(st.session_state.db_clientes.keys()) if st.session_state.db_clientes else ["Varios"]
                cl_sel = st.selectbox("Cliente que realiza el abono:", cl_list)
                monto_op = st.number_input("Monto Recaudado ($ COP):", min_value=0.0)
                modo_pago = "Contado"
                vence_op = date.today()

            elif st.session_state.frente == "PAGO":
                pr_list = list(st.session_state.db_proveedores.keys()) if st.session_state.db_proveedores else ["Varios"]
                prov_sel = st.selectbox("Proveedor al que se le paga:", pr_list)
                monto_op = st.number_input("Monto Pagado ($ COP):", min_value=0.0)
                modo_pago = "Contado"
                vence_op = date.today()

            asentar = st.form_submit_button("💾 ASENTAR EN LIBRO DIARIO")
            
        if asentar:
            id_trans = int(datetime.now().timestamp())
            nuevo_asiento = {"id": id_trans, "Fecha": str(fecha_op), "Frente": st.session_state.frente, "Modo": modo_pago, "Vence": str(vence_op)}
            
            if st.session_state.frente == "COMPRA":
                total = cant_c * costo_c
                nuevo_asiento.update({"Tercero": prov_sel, "Detalle": prod_compra, "Cantidad": cant_c, "Valor_U": costo_c, "Total": total, "Costo_Venta": 0.0})
                # Actualizar base de datos de inventario real
                if prod_compra in st.session_state.db_inventario:
                    st.session_state.db_inventario[prod_compra]["cantidad"] += cant_c
                else:
                    st.session_state.db_inventario[prod_compra] = {"cantidad": cant_c, "costo_u": costo_c, "ventas_unidades": 0}
                if prov_sel not in st.session_state.db_proveedores:
                    st.session_state.db_proveedores[prov_sel] = 0.0

            elif st.session_state.frente == "VENTA":
                total = cant_v * precio_v
                costo_asoc = st.session_state.db_inventario.get(prod_venta, {}).get("costo_u", 0.0) * cant_v
                nuevo_asiento.update({"Tercero": cl_sel, "Detalle": prod_venta, "Cantidad": cant_v, "Valor_U": precio_v, "Total": total, "Costo_Venta": costo_asoc})
                # Descontar stock real
                if prod_venta in st.session_state.db_inventario:
                    st.session_state.db_inventario[prod_venta]["cantidad"] -= cant_v
                    st.session_state.db_inventario[prod_venta]["ventas_unidades"] += cant_v

            elif st.session_state.frente == "GASTO":
                detalle_f = f"{tipo_g} ({detalle_g})" if tipo_g == "Servicio Público" else tipo_g
                nuevo_asiento.update({"Tercero": "Gasto Operacional", "Detalle": detalle_f, "Cantidad": 1, "Valor_U": valor_g, "Total": valor_g, "Costo_Venta": 0.0})

            elif st.session_state.frente == "COBRO":
                nuevo_asiento.update({"Tercero": cl_sel, "Detalle": "Recaudo de Cartera", "Cantidad": 1, "Valor_U": monto_op, "Total": monto_op, "Costo_Venta": 0.0})

            elif st.session_state.frente == "PAGO":
                nuevo_asiento.update({"Tercero": prov_sel, "Detalle": "Cancelación de Obligación", "Cantidad": 1, "Valor_U": monto_op, "Total": monto_op, "Costo_Venta": 0.0})

            st.session_state.libro_diario.append(nuevo_asiento)
            st.success("Transacción asentada en la matriz diaria con éxito.")
            st.rerun()

    st.markdown("---")

    # =========================================================================
    # FASE 3: DIARIO HISTÓRICO CON AUDITORÍA (CORREGIR PARTIDAS)
    # =========================================================================
    st.subheader("📖 Matriz del Libro Diario y Auditoría")
    if st.session_state.libro_diario:
        df_diario = pd.DataFrame(st.session_state.libro_diario)
        
        # Mapeo de columnas visuales
        st.dataframe(df_diario[["Fecha", "Frente", "Tercero", "Detalle", "Cantidad", "Valor_U", "Total", "Modo", "Vence"]], use_container_width=True)
        
        # Sistema de Corrección por Partida Específica
        st.markdown("**⚙️ Zona de Auditoría Operativa:**")
        col_au1, col_au2 = st.columns([2, 2])
        idx_del = col_au1.selectbox("Seleccione el asiento a eliminar o corregir:", options=range(len(st.session_state.libro_diario)), format_func=lambda i: f"Asiento {i}: {st.session_state.libro_diario[i]['Frente']} - {st.session_state.libro_diario[i]['Tercero']} (${st.session_state.libro_diario[i]['Total']:,.0f})")
        if col_au1.button("🗑️ Eliminar Partida Seleccionada"):
            partida_eliminada = st.session_state.libro_diario.pop(idx_del)
            # Revertir stock si fue venta o compra
            if partida_eliminada["Frente"] == "VENTA" and partida_eliminada["Detalle"] in st.session_state.db_inventario:
                st.session_state.db_inventario[partida_eliminada["Detalle"]]["cantidad"] += partida_eliminada["Cantidad"]
                st.session_state.db_inventario[partida_eliminada["Detalle"]]["ventas_unidades"] -= partida_eliminada["Cantidad"]
            elif partida_eliminada["Frente"] == "COMPRA" and partida_eliminada["Detalle"] in st.session_state.db_inventario:
                st.session_state.db_inventario[partida_eliminada["Detalle"]]["cantidad"] -= partida_eliminada["Cantidad"]
            st.warning("Partida eliminada y balances de inventario revertidos automáticamente.")
            st.rerun()
            
        csv_data = df_diario.to_csv(index=False).encode('utf-8')
        col_au2.download_button("📥 Descargar Reporte de Transacciones (CSV)", data=csv_data, file_name=f"libro_diario_{st.session_state.negocio}.csv", mime="text/csv")
    else:
        st.info("No se registran transacciones contables registradas en el día.")

    st.markdown("---")

    # =========================================================================
    # FASE 4: RECOMENDADOR IA Y ALERTAS AUTOMATIZADAS (WHATSAPP)
    # =========================================================================
    st.subheader("💡 Asesoría Financiera Inteligente y Alertas Tempranas")
    col_as1, col_as2 = st.columns(2)
    
    with col_as1:
        st.markdown("### 🔔 Módulo de Alertas Críticas (Vencimientos)")
        hoy = date.today()
        
        # Alertas de Inventario Crítico
        for prod, info in st.session_state.db_inventario.items():
            if info["cantidad"] <= 2:
                st.markdown(f"<div class='alert-warn'>⚠️ <b>Alerta de Inventario:</b> El producto '{prod}' está próximo a ruptura de stock ({info['cantidad']} unidades restantes).</div>", unsafe_allow_html=True)
        
        # Alertas de Cuentas por Cobrar (Ventas Crédito)
        for asiento in st.session_state.libro_diario:
            if asiento["Frente"] == "VENTA" and asiento["Modo"] == "Crédito":
                f_vence = datetime.strptime(asiento["Vence"], "%Y-%m-%d").date()
                if f_vence <= hoy:
                    st.markdown(f"<div class='alert-warn'>⏳ <b>Cartera Vencida:</b> {asiento['Tercero']} presenta una deuda de ${asiento['Total']:,.0f} COP.</div>", unsafe_allow_html=True)
                    msg_wa = f"Estimado {asiento['Tercero']}, le recordamos amablemente que su saldo de ${asiento['Total']:,.0f} COP con {st.session_state.negocio} venció el {asiento['Vence']}. Agradecemos su gestión de pago."
                    link = f"https://wa.me/?text={msg_wa.replace(' ', '%20')}"
                    st.markdown(f"[📲 Enviar Recordatorio de Cobro vía WhatsApp]({link})")

            # Alertas de Facturas de Servicios / Proveedores Vencidas
            if asiento["Modo"] == "Crédito" and asiento["Frente"] == "COMPRA":
                f_vence = datetime.strptime(asiento["Vence"], "%Y-%m-%d").date()
                if f_vence <= hoy:
                    st.markdown(f"<div class='alert-warn'>🔴 <b>Obligación Vencida con Proveedor:</b> Deuda con {asiento['Tercero']} por ${asiento['Total']:,.0f} COP venció hoy. Prorrogue o liquide para evitar bloqueos de suministro.</div>", unsafe_allow_html=True)

    with col_as2:
        st.markdown("### 🧠 Recomendaciones Analíticas de Ruta Estratégica")
        if st.session_state.db_inventario:
            df_inv_analisis = pd.DataFrame.from_dict(st.session_state.db_inventario, orient='index')
            prod_estrella = df_inv_analisis['ventas_unidades'].idxmax()
            prod_lento = df_inv_analisis['ventas_unidades'].idxmin()
            
            if df_inv_analisis['ventas_unidades'].max() > 0:
                st.success(f"⭐ **Ruta de Alta Rotación:** El producto '{prod_estrella}' es el más vendido del período. Recomendación: Incremente un 20% el capital de trabajo destinado a este ítem para blindar su cadena de suministro.")
                st.error(f"📉 **Alerta de Inmovilizado:** El artículo '{prod_lento}' muestra nula o muy baja rotación en el mercado. Recomendación: Libere flujo de caja ejecutando promociones cruzadas o combos con el producto estrella.")
            else:
                st.info("El Asesor IA está esperando mayor volumen de transacciones de venta para generar patrones de optimización de inventarios.")
        else:
            st.info("Cargue productos en el inventario para activar el motor de estrategia.")

    st.markdown("---")

    # =========================================================================
    # FASE 5: ESTADOS FINANCIEROS DINÁMICOS COMPLETOS
    # =========================================================================
    st.subheader("📊 Estados Financieros Generados de Forma Automática")
    t1, t2, t3 = st.tabs(["📋 Estado de Resultados", "⚖️ Balance General", "💸 Flujo de Caja (Método Directo)"])
    
    # Cálculos Financieros Consolidados
    ingresos_totales = sum(a["Total"] for a in st.session_state.libro_diario if a["Frente"] == "VENTA")
    costo_ventas_total = sum(a.get("Costo_Venta", 0.0) for a in st.session_state.libro_diario if a["Frente"] == "VENTA")
    gastos_totales = sum(a["Total"] for a in st.session_state.libro_diario if a["Frente"] == "GASTO")
    utilidad_neta = ingresos_totales - costo_ventas_total - gastos_totales
    
    val_inventario_actual = sum(v["cantidad"] * v["costo_u"] for v in st.session_state.db_inventario.values())

    with t1:
        st.markdown("#### Estado de Resultados Integral")
        st.markdown(f"""
        | Cuenta Contable | Valor Nominal |
        | :--- | :--- |
        | **(+) Ingresos de Actividades Ordinarias (Ventas)** | ${ingresos_totales:,.2f} COP |
        | **(-) Costo de Ventas (Inventario Consumido)** | ${costo_ventas_total:,.2f} COP |
        | **(=) UTILIDAD BRUTA** | **${(ingresos_totales - costo_ventas_total):,.2f} COP** |
        | **(-) Gastos Operacionales (Servicios, Arriendos, Nóminas)** | ${gastos_totales:,.2f} COP |
        | **(=) UTILIDAD NETA DEL EJERCICIO** | **${utilidad_neta:,.2f} COP** |
        """)

    with t2:
        st.markdown("#### Balance General")
        total_activos = caja_actual + cartera_actual + val_inventario_actual
        total_pasivos = proveedores_actual
        patrimonio_neto = total_activos - total_pasivos
        
        st.markdown(f"""
        | ACTIVO (Estructura de Inversión) | | PASIVO Y PATRIMONIO (Estructura de Financiación) | |
        | :--- | :--- | :--- | :--- |
        | 💵 Caja y Efectivo Disponible | ${caja_actual:,.2f} COP | 🏭 Obligaciones Proveedores (Pasivo) | ${total_pasivos:,.2f} COP |
        | 👥 Cartera Comercial (Clientes) | ${cartera_actual:,.2f} COP | | |
        | 📦 Inventarios Valorados Real | ${val_inventario_actual:,.2f} COP | ⚖️ Patrimonio Líquido / Neto | ${patrimonio_neto:,.2f} COP |
        | **TOTAL ACTIVOS** | **${total_activos:,.2f} COP** | **TOTAL PASIVOS + PATRIMONIO** | **${(total_pasivos + patrimonio_neto):,.2f} COP** |
        """)

    with t3:
        st.markdown("#### Flujo de Caja Mensual")
        entradas_efectivo = sum(a["Total"] for a in st.session_state.libro_diario if a["Frente"] == "COBRO" or (a["Frente"] == "VENTA" and a["Modo"] == "Contado"))
        salidas_efectivo = sum(a["Total"] for a in st.session_state.libro_diario if a["Frente"] in ["PAGO", "GASTO"] or (a["Frente"] == "COMPRA" and a["Modo"] == "Contado"))
        flujo_neto_efectivo = entradas_efectivo - salidas_efectivo
        
        st.markdown(f"""
        * **Efectivo Neto de Apertura (Caja Inicial):** ${st.session_state.caja_inicial:,.2f} COP
        * **(+) Flujos de Efectivo por Actividades de Operación (Recaudos/Ventas):** ${entradas_efectivo:,.2f} COP
        * **(-) Flujos de Efectivo Aplicados a Operación (Pagos/Compras/Gastos):** ${salidas_efectivo:,.2f} COP
        * **(=) INCREMENTO / DISMINUCIÓN NETO DE EFECTIVO:** **${flujo_neto_efectivo:,.2f} COP**
        * **💵 SALDO FINAL DISPONIBLE EN CAJA:** **${caja_actual:,.2f} COP**
        """)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Reiniciar Aplicación y Limpiar Memoria"):
        st.session_state.clear()
        st.rerun()