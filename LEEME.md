# Asesor Financiero IA - Micronegocio

## Cómo ejecutar

1. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

2. Corre la app:
   ```
   streamlit run app.py
   ```

3. Se abrirá en http://localhost:8501

## Estructura del proyecto

- `app.py` — App de Streamlit (interfaz + lógica del cuaderno digital)
- `predictor.py` — Módulo de inferencia: carga los modelos y expone funciones de predicción
- `modelos/` — Los 4 modelos ya entrenados (.pkl), listos para usar
- `ml/generar_datos_sinteticos.py` — Genera los datos sintéticos de entrenamiento
- `ml/entrenar_modelos.py` — Entrena los 4 modelos desde cero

## Los 4 modelos predictivos

| Modelo | Qué predice | Desempeño (datos sintéticos) |
|---|---|---|
| `modelo_flujo_caja.pkl` | Flujo de caja neto de los próximos 7 días | R² = 0.79 |
| `modelo_riesgo_cliente.pkl` | Probabilidad de que un fiado se pague tarde | AUC = 0.60 |
| `modelo_demanda_inventario.pkl` | Demanda esperada por artículo (próx. 7 días) | R² = 0.74 |
| `modelo_ccc.pkl` | Proyección del Ciclo de Conversión de Caja a 15 días | R² = 0.88 |

## Nota metodológica importante para la tesis

Los modelos se entrenaron con **datos sintéticos** que simulan 60 micronegocios
tipo tienda de barrio durante 180 días (ver `ml/generar_datos_sinteticos.py`).
Esto sirve como:

1. Prueba de concepto de que la arquitectura (features → modelo → predicción
   → traducción en lenguaje natural) funciona de punta a punta.
2. Línea base metodológica citable en el marco metodológico de la tesis.

Para la versión final, se recomienda re-entrenar `ml/entrenar_modelos.py` con
datos reales (encuestas a microempresarios de Barranquilla, o históricos de
cuadernos digitales existentes), simplemente reemplazando los CSV que genera
`generar_datos_sinteticos.py` por datos reales con las mismas columnas.

El desempeño del modelo de riesgo de mora (AUC=0.60) es modesto porque el
comportamiento de pago simulado tiene un componente aleatorio grande; con datos
reales y más historial por cliente debería mejorar.
