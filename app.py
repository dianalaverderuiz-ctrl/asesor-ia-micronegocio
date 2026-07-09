# ==============================================================================
# SISTEMA GENERAL MVP: ENFOQUE DE CUATRO PUNTAS CON ALERTAS OPERATIVAS AUTOMÁTICAS
# ==============================================================================
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

# Configuración del entorno táctil de la aplicación móvil
st.set_page_config(page_title="Asesor IA - Ciclo Financiero", page_icon="📲", layout="centered")

# ==============================================================================
# INICIALIZACIÓN DEL MOTOR DE PERSISTENCIA (SESSION STATE)
# ==============================================================================
if "configurado" not in st.session_state:
    st.session_state.configurado = False
    st.session_state.nombre = ""
    st.session_state.negocio = ""
    st.session_state.dia_actual = 1
    
    # Catálogos maestros para indexación futura (Autocompletado)
    st.session_state.cat_clientes = []
    st.session_state.cat_proveedores = []
    st.session_state.cat_articulos = []
    
    # Estructura del Estado Financiero e Historiales
    st.session_state.saldo_caja = 0
    st.session_state.inventario_stock = 0
    st.session_state.registro_ventas = []
    st.session_state.registro_compras = []
    st.session_state.registro_recaudos = []
    st.session_state.registro_gastos = []

def obtener_fecha_simulada():
    fecha_base = datetime(2026, 6, 1)
    return fecha_base + timedelta(days=st.session_state.dia_actual - 1)

def fmt_moneda(valor):
    return f"${valor:,.0f} COP"

# ==============================================================================
# FASE 1: CONFIGURACIÓN DE PERFIL Y ESTABLECIMIENTO DE SALDOS INICIALES
# ==============================================================================
if not st.session_state.configurado:
    st.title("📲 Inicialización del Negocio")
    st.write("Configure los parámetros iniciales de control para los módulos financieros.")
    
    st.session_state.nombre = st.text_input("Nombre de la Persona:", placeholder="Ej. Diana")
    st.session_state.negocio = st.text_input("Nombre del Negocio:", placeholder="Ej. Tienda Caribe")
    
    st.markdown("---")
    st.write("#### 💰 Configuración de Saldos Iniciales Base")
    st.session_state.saldo_caja = st.number_input("Saldo Inicial en Caja ($):", min_value=0, value=500000, step=50000)
    st.session_state.inventario_stock = st.number_input("Valor Inicial del Inventario ($):", min_value=0, value=1200000, step=100000)
    
    if st.button("Guardar Parámetros e Iniciar App", type="primary"):
        if st.session_state.nombre and st.session_state.negocio:
            st.session_state.configurado = True
            st.rerun()
        else:
            st.error("Por favor, complete los campos de nombre y negocio.")

# ==============================================================================
# ENTORNO OPERATIVO: CONTROL DIARIO, SEMANAL Y MENSUAL
# ==============================================================================
else:
    fecha_hoy = obtener_fecha_simulada()
    st.title(f"🏢 {st.session_state.negocio}")
    
    # Notificación proactiva diaria en el banner superior
    st.info(f"🔔 **[ALERTA DIARIA - 7:00 AM]**\n🤖 ¡Epa {st.session_state.nombre}! No olvides registrar los movimientos del día de hoy: **{fecha_hoy.strftime('%d/%m/%Y')}** (Día {st.session_state.dia_actual} del ciclo).")
    
    # ─── PANEL GENERAL DE SALDOS EN TIEMPO REAL (ACCESO CON UN CLICK) ───
    with st.expander("📊 CLIC AQUÍ PARA CONSULTAR SALDOS ACTUALES DE LOS MÓDULOS", expanded=True):
        c_cobrar_tot = sum(v["monto"] for v in st.session_state.registro_ventas if v["tipo"] == "Crédito") - sum(r["monto"] for r in st.session_state.registro_recaudos)
        c_pagar_tot = sum(c["monto"] for c in st.session_state.registro_compras if c["condicion"] == "Crédito")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📦 Inventario", fmt_moneda(st.session_state.inventario_stock))
        m2.metric("💵 Caja", fmt_moneda(st.session_state.saldo_caja))
        m3.metric("💸 Por Cobrar", fmt_moneda(c_cobrar_tot))
        m4.metric("📉 Por Pagar", fmt_moneda(c_pagar_tot))

    # ─── ENTRADA GENERAL DE CATÁLOGOS MAESTROS ───
    with st.expander("➕ Módulo de Creación: Clientes, Proveedores y Artículos"):
        tipo_creacion = st.radio("¿Qué desea registrar en la base de datos?", ["Cliente", "Proveedor", "Artículo"], horizontal=True)
        if tipo_creacion == "Cliente":
            nuevo_cli = st.text_input("Nombre Completo del Cliente:").strip().capitalize()
            if st.button("Añadir Cliente") and nuevo_cli:
                if nuevo_cli not in st.session_state.cat_clientes:
                    st.session_state.cat_clientes.append(nuevo_cli)
                    st.success(f"Cliente '{nuevo_cli}' creado.")
        elif tipo_creacion == "Proveedor":
            nuevo_prov = st.text_input("Nombre del Proveedor:").strip().upper()
            if st.button("Añadir Proveedor") and nuevo_prov:
                if nuevo_prov not in st.session_state.cat_proveedores:
                    st.session_state.cat_proveedores.append(nuevo_prov)
                    st.success(f"Proveedor '{nuevo_prov}' registrado.")
        elif tipo_creacion == "Artículo":
            nuevo_art = st.text_input("Nombre / Detalle del Artículo:").strip()
            if st.button("Añadir Artículo") and nuevo_art:
                if nuevo_art not in st.session_state.cat_articulos:
                    st.session_state.cat_articulos.append(nuevo_art)
                    st.success(f"Artículo '{nuevo_art}' catalogado.")

    st.markdown("---")
    
    # ==============================================================================
    # INTERFAZ DE LAS CUATRO PUNTAS OPERATIVAS DEL CICLO FINANCIERO
    # ==============================================================================
    st.write("### ⚙️ Ciclo de Operaciones")
    punta = st.selectbox("Seleccione el módulo a gestionar:", ["1. COMPRA (Inventarios y Proveedores)", "2. VENDE (Descargue e Ingresos)", "3. RECAUDA (Contado y Crédito)", "4. PAGA (Gastos recurrentes y fijos)"])
    
    # ─── PUNTA 1: COMPRA ───
    if "COMPRA" in punta:
        with st.form("form_compra", clear_on_submit=True):
            st.write("#### Registrar Compra de Mercancía o Insumos")
            prov = st.selectbox("Seleccione el Proveedor:", [""] + st.session_state.cat_proveedores)
            condicion = st.radio("Condición de Pago:", ["Contado", "Crédito"])
            insumo = st.text_input("Detalle de la Mercancía:")
            monto = st.number_input("Monto Total de la Compra ($):", min_value=0, step=10000)
            
            if st.form_submit_button("Guardar Operación de Compra"):
                if prov and insumo and monto > 0:
                    st.session_state.inventario_stock += monto
                    if condicion == "Contado":
                        st.session_state.saldo_caja -= monto
                    st.session_state.registro_compras.append({"fecha": fecha_hoy.strftime('%Y-%m-%d'), "proveedor": prov, "condicion": condicion, "monto": monto, "insumo": insumo})
                    st.success("✔ Compra registrada exitosamente.")
                    st.rerun()
                else: st.error("Complete todos los campos del formulario.")

    # ─── PUNTA 2: VENDE ───
    elif "VENDE" in punta:
        with st.form("form_vende", clear_on_submit=True):
            st.write("#### Registrar Venta y Descargue de Inventario")
            cli = st.selectbox("Seleccione el Cliente:", [""] + st.session_state.cat_clientes)
            art = st.selectbox("Seleccione el Artículo:", [""] + st.session_state.cat_articulos)
            tipo_v = st.radio("Tipo de Venta:", ["Contado", "Crédito"])
            monto = st.number_input("Valor de la Transacción ($):", min_value=0, step=10000)
            
            # Subcampo interactivo condicionado para ventas a crédito
            fecha_venc = st.date_input("Fecha de Vencimiento del Crédito:", value=fecha_hoy + timedelta(days=15)) if tipo_v == "Crédito" else None
            
            if st.form_submit_button("Guardar Operación de Venta"):
                if cli and art and monto > 0:
                    st.session_state.inventario_stock = max(0, st.session_state.inventario_stock - (monto * 0.6))  # Costo estimado de descarga
                    if tipo_v == "Contado":
                        st.session_state.saldo_caja += monto
                    
                    st.session_state.registro_ventas.append({
                        "fecha": fecha_hoy.strftime('%Y-%m-%d'), "cliente": cli, "tipo": tipo_v, 
                        "monto": monto, "articulo": art, "vencimiento": fecha_venc.strftime('%Y-%m-%d') if fecha_venc else None
                    })
                    st.success("✔ Venta procesada correctamente.")
                    st.rerun()
                else: st.error("Complete la información básica de la venta.")

    # ─── PUNTA 3: RECAUDA ───
    elif "RECAUDA" in punta:
        with st.form("form_recauda", clear_on_submit=True):
            st.write("#### Registrar Recaudo de Carteras de Clientes")
            cli = st.selectbox("Seleccione el Cliente que paga:", [""] + st.session_state.cat_clientes)
            monto = st.number_input("Monto Recibido en Efectivo ($):", min_value=0, step=10000)
            
            if st.form_submit_button("Guardar Recaudo"):
                if cli and monto > 0:
                    st.session_state.saldo_caja += monto
                    st.session_state.registro_recaudos.append({"fecha": fecha_hoy.strftime('%Y-%m-%d'), "cliente": cli, "monto": monto})
                    st.success(f"✔ Recaudo abonado a la cuenta de {cli}.")
                    st.rerun()

    # ─── PUNTA 4: PAGA ───
    elif "PAGA" in punta:
        with st.form("form_paga", clear_on_submit=True):
            st.write("#### Registrar Salidas por Gastos")
            clase_g = st.selectbox("Clasificación del Gasto:", ["Servicios públicos", "Nóminas", "Arriendos", "Otros egresos"])
            monto = st.number_input("Valor del Pago ($):", min_value=0, step=10000)
            recurrente = st.checkbox("¿Es un gasto de carácter recurrente?")
            prox_pago = st.date_input("Fecha estimada del próximo pago:", value=fecha_hoy + timedelta(days=30))
            obs = st.text_input("Observación cualitativa del gasto:", placeholder="Ej. Tarifa de luz mes corriente")
            
            if st.form_submit_button("Guardar Gasto"):
                if monto > 0:
                    st.session_state.saldo_caja -= monto
                    st.session_state.registro_gastos.append({
                        "fecha": fecha_hoy.strftime('%Y-%m-%d'), "clase": clase_g, "monto": monto,
                        "recurrente": recurrente, "prox_pago": prox_pago.strftime('%Y-%m-%d') if recurrente else None, "obs": obs
                    })
                    st.success("✔ Gasto indexado en la bitácora.")
                    st.rerun()

    # ==============================================================================
    # FASE 3: PIPELINE CRONOMETRADO DE ALERTAS Y SEGUIMIENTO SEMANAL
    # ==============================================================================
    st.markdown("---")
    c_av, c_mes = st.columns(2)
    
    if c_av.button("⏩ Avanzar Jornada Laboral (Día)", use_container_width=True):
        if st.session_state.dia_actual < 30:
            st.session_state.dia_actual += 1
            st.rerun()

    if c_mes.button("📊 Forzar Cierre y Balance Mensual (Día 30)", use_container_width=True, type="primary"):
        st.session_state.dia_actual = 30
        st.rerun()

    # --- MOTOR DE ALERTAS FINANCIERAS Y ENLACES DE COBRO POR WHATSAPP ---
    st.write("### 🚨 Sistema de Alertas de Vencimiento y Proveedores")
    
    # 1. Alertas de Cuentas por Cobrar con Botón de WhatsApp
    for v in st.session_state.registro_ventas:
        if v["tipo"] == "Crédito":
            f_venc = datetime.strptime(v["vencimiento"], '%Y-%m-%d')
            if fecha_hoy >= f_venc:
                # Generar el mensaje automatizado para el cliente
                msg_wa = f"Hola {v['cliente']}, un saludo de {st.session_state.negocio}. Te recordamos que la cuenta por valor de {fmt_moneda(v['monto'])} por concepto de {v['articulo']} venció el {f_venc.strftime('%d/%m/%Y')}. Agradecemos tu valioso pago."
                url_wa = f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_wa)}"
                
                st.warning(f"⚠️ **Crédito Vencido:** {v['cliente']} debe {fmt_moneda(v['monto'])} desde el {f_venc.strftime('%d/%m/%Y')}.")
                st.markdown(f"[📲 Enviar Recordatorio de Cobro vía WhatsApp]({url_wa})")

    # 2. Alertas de Costos y Gastos Recurrentes
    for g in st.session_state.registro_gastos:
        if g["recurrente"]:
            f_prox = datetime.strptime(g["prox_pago"], '%Y-%m-%d')
            if (f_prox - fecha_hoy).days <= 3:
                st.error(f"📉 **Recordatorio de Pago:** Tu gasto recurrente de '{g['clase']}' tiene una fecha estimada de pago el {f_prox.strftime('%d/%m/%Y')} por valor de {fmt_moneda(g['monto'])}.")

    # 3. Reporte de Flujo de Caja Semanal Automático
    if st.session_state.dia_actual in [7, 14, 21, 28]:
        st.subheader(f"📊 Resumen del Flujo de Caja de la Semana {st.session_state.dia_actual // 7}")
        ing_sem = sum(v["monto"] for v in st.session_state.registro_ventas if v["tipo"] == "Contado") + sum(r["monto"] for r in st.session_state.registro_recaudos)
        egr_sem = sum(c["monto"] for c in st.session_state.registro_compras if c["condicion"] == "Contado") + sum(g["monto"] for g in st.session_state.registro_gastos)
        st.metric("Flujo Neto Semanal", fmt_moneda(ing_sem - egr_sem))

    # ==============================================================================
    # FASES 4 Y 5: REPORTES MENSUALES COMPILADOS Y DESCARGABLES (.CSV)
    # ==============================================================================
    if st.session_state.dia_actual >= 30:
        st.markdown("---")
        st.header("📋 Informes y Estados Financieros del Ciclo")
        
        v_tot = sum(d["monto"] for d in st.session_state.registro_ventas)
        c_tot = sum(d["monto"] for d in st.session_state.registro_compras)
        g_tot = sum(d["monto"] for d in st.session_state.registro_gastos)
        u_neta = (v_tot - (c_tot * 0.6)) - g_tot
        
        t1, t2 = st.tabs(["📈 Estado de Resultados", "🏛️ Balance General y Métricas"])
        
        with t1:
            st.write(f"**(+) Ingreso Operativo por Ventas:** {fmt_moneda(v_tot)}")
            st.write(f"**(-) Costo Estimado de Ventas:** {fmt_moneda(c_tot * 0.6)}")
            st.write(f"**(-) Gastos de Local y Administración:** {fmt_moneda(g_tot)}")
            st.markdown(f"### **UTILIDAD NETO DEL MES:** {fmt_moneda(u_neta)}")
            
        with t2:
            st.write(f"**• Dinero en Caja:** {fmt_moneda(st.session_state.saldo_caja)}")
            st.write(f"**• Inventarios Valorizados:** {fmt_moneda(st.session_state.inventario_stock)}")
            st.markdown(f"#### 🎯 Indicadores Explicados por la IA:")
            st.write(f"* **KTNO (Capital de Trabajo):** {fmt_moneda(st.session_state.inventario_stock + c_cobrar_tot)}. Representa los recursos que posees amarrados para abrir tu negocio mañana.")

        # --- SECCIÓN DE DESCARGAS DE REPORTES PARA EL MICROEMPRESARIO ---
        st.write("### 📥 Módulo de Descarga de Datos (Exportar Informes)")
        if st.session_state.registro_ventas:
            df_v = pd.DataFrame(st.session_state.registro_ventas)
            st.download_button("Descargar Informe de Ventas (.CSV)", data=df_v.to_csv(index=False).encode('utf-8'), file_name="ventas_mes.csv", mime="text/csv")
        if st.session_state.registro_gastos:
            df_g = pd.DataFrame(st.session_state.registro_gastos)
            st.download_button("Descargar Informe de Gastos (.CSV)", data=df_g.to_csv(index=False).encode('utf-8'), file_name="gastos_mes.csv", mime="text/csv")