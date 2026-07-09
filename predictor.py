"""
Módulo de inferencia del Asesor Financiero IA.

Carga los 4 modelos entrenados (ver carpeta /modelos) y expone funciones
simples que la app de Streamlit puede llamar directamente con los datos
que ya existen en st.session_state, sin que la interfaz tenga que saber
nada de scikit-learn.
"""

import os
import joblib
import numpy as np
import pandas as pd

MODELOS_DIR = os.path.join(os.path.dirname(__file__), "modelos")

_cache = {}


def _cargar(nombre_archivo):
    if nombre_archivo not in _cache:
        ruta = os.path.join(MODELOS_DIR, nombre_archivo)
        _cache[nombre_archivo] = joblib.load(ruta)
    return _cache[nombre_archivo]


def modelos_disponibles():
    """True si los 4 archivos .pkl existen en disco."""
    archivos = [
        "modelo_flujo_caja.pkl",
        "modelo_riesgo_cliente.pkl",
        "modelo_demanda_inventario.pkl",
        "modelo_ccc.pkl",
    ]
    return all(os.path.exists(os.path.join(MODELOS_DIR, a)) for a in archivos)


# ------------------------------------------------------------------
# 1. Flujo de caja futuro (próximos 7 días)
# ------------------------------------------------------------------
def predecir_flujo_caja(dia_semana, caja, venta_contado_hoy, venta_credito_hoy,
                         prom_venta_7d, prom_gasto_7d, prom_compra_7d,
                         cartera_actual, inventario_valor):
    paquete = _cargar("modelo_flujo_caja.pkl")
    modelo, features = paquete["modelo"], paquete["features"]

    fila = pd.DataFrame([{
        "dia_semana": dia_semana,
        "caja": caja,
        "venta_contado": venta_contado_hoy,
        "venta_credito": venta_credito_hoy,
        "prom_venta_7d": prom_venta_7d,
        "prom_gasto_7d": prom_gasto_7d,
        "prom_compra_7d": prom_compra_7d,
        "cartera_actual": cartera_actual,
        "inventario_valor": inventario_valor,
    }])[features]

    return float(modelo.predict(fila)[0])


# ------------------------------------------------------------------
# 2. Riesgo de mora de un cliente (fiado)
# ------------------------------------------------------------------
def predecir_riesgo_cliente(monto_credito, plazo_dias, pagos_tardios_previos,
                             pagos_totales_previos, monto_promedio_cliente,
                             prop_credito_negocio):
    paquete = _cargar("modelo_riesgo_cliente.pkl")
    modelo, features = paquete["modelo"], paquete["features"]

    tasa_mora_previa = pagos_tardios_previos / max(pagos_totales_previos, 1)

    fila = pd.DataFrame([{
        "monto_credito": monto_credito,
        "plazo_dias": plazo_dias,
        "pagos_tardios_previos": pagos_tardios_previos,
        "pagos_totales_previos": pagos_totales_previos,
        "tasa_mora_previa": tasa_mora_previa,
        "monto_promedio_cliente": monto_promedio_cliente,
        "prop_credito_negocio": prop_credito_negocio,
    }])[features]

    return float(modelo.predict_proba(fila)[0, 1])


# ------------------------------------------------------------------
# 3. Demanda esperada de un artículo (próximos 7 días)
# ------------------------------------------------------------------
def predecir_demanda_articulo(articulo, dia_semana, stock_actual, prom_demanda_7d):
    paquete = _cargar("modelo_demanda_inventario.pkl")
    modelo, features, le = paquete["modelo"], paquete["features"], paquete["label_encoder"]

    if articulo in le.classes_:
        articulo_cod = int(le.transform([articulo])[0])
    else:
        # Artículo no visto en el entrenamiento: se usa el promedio general
        articulo_cod = int(np.median(range(len(le.classes_))))

    fila = pd.DataFrame([{
        "articulo_cod": articulo_cod,
        "dia_semana": dia_semana,
        "stock_actual": stock_actual,
        "prom_demanda_7d": prom_demanda_7d,
    }])[features]

    return max(0.0, float(modelo.predict(fila)[0]))


# ------------------------------------------------------------------
# 4. Proyección del CCC (Ciclo de Conversión de Caja)
# ------------------------------------------------------------------
def predecir_ccc(dso, dio, dpo, cartera_actual, inventario_valor, prom_venta_15d):
    paquete = _cargar("modelo_ccc.pkl")
    modelo, features = paquete["modelo"], paquete["features"]

    fila = pd.DataFrame([{
        "dso": dso,
        "dio": dio,
        "dpo": dpo,
        "cartera_actual": cartera_actual,
        "inventario_valor": inventario_valor,
        "prom_venta_15d": prom_venta_15d,
    }])[features]

    return float(modelo.predict(fila)[0])


def calcular_dso_dio_dpo(cartera_actual, inventario_valor, ventas_recientes, costo_ventas_recientes, dpo_estimado=20):
    """
    Calcula DSO y DIO a partir de datos actuales del negocio (ventana de 15 días),
    usando las fórmulas estándar del Ciclo de Conversión de Caja:
      DSO = (Cuentas por Cobrar / Ventas del periodo) * días del periodo
      DIO = (Inventario / Costo de Ventas del periodo) * días del periodo
    dpo_estimado se deja como parámetro editable porque esta app aún no
    lleva un histórico detallado de plazos pactados con cada proveedor.
    """
    dias_periodo = 15
    dso = (cartera_actual / ventas_recientes) * dias_periodo if ventas_recientes > 0 else 0
    dio = (inventario_valor / costo_ventas_recientes) * dias_periodo if costo_ventas_recientes > 0 else 0
    ccc = dso + dio - dpo_estimado
    return dso, dio, ccc
