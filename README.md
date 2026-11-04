# Kairos KuCoin MCP 1.1.1

Release de código: cuatro herramientas MCP registradas y Docker corregido.
Solo datos públicos; no claves de exchange, saldos privados, órdenes o transferencias.

## Corrección

El ZIP 1.1.0 registra cuatro herramientas, pero su Dockerfile solo copiaba server.py
 y market_data.py: faltaban history_data.py y technical.py. En una construcción
limpia ese paquete no podía importar el servidor histórico correctamente.
Este release copia los cuatro módulos necesarios y añade pruebas de descubrimiento
MCP con FastMCP 2.14.7. Service info devuelve versión 1.1.1 y catálogo esperado.
El catálogo esperado es diagnóstico: la prueba real es tools/list.

No se ha identificado qué código está ejecutándose en el servicio actual ni si
ChatGPT conserva un catálogo anterior. La corrección del ZIP no demuestra por sí
sola la causa de que solo aparezcan dos herramientas en la conexión existente.

## Actualizar el servicio existente

1. Descomprimir y reemplazar los archivos del repositorio MCP por el contenido
   de kairos-kucoin-connector. No subir el ZIP como único archivo del repositorio.
2. Mantener Root Directory apuntando a la carpeta del Dockerfile y conservar URL,
   variables y servicio actuales. No modificar el repositorio ni servicio KairosWeb.
3. Desplegar el commit nuevo en el servicio KuCoin de Render. Si aparece un build
   antiguo, utilizar un nuevo build sin caché desde el panel disponible.
4. Ejecutar el verificador del catálogo remoto:

```bash
python -m pip install -r requirements.txt
python verify_tools.py https://TU-SERVICIO.onrender.com/mcp
```

Debe devolver status OK, versión 1.1.1 y exactamente cuatro herramientas. No consulta
precios ni históricos upstream. Si no coincide, revisar commit, Root Directory,
Dockerfile y URL efectiva. No repetir llamadas durante pausas de un proveedor.
5. Actualizar la conexión MCP en ChatGPT mediante la opción de refrescar herramientas
   que ofrezca la cuenta y verificar en una conversación nueva. Si sigue mostrando
   dos, revisar la conexión/catálogo de ChatGPT antes de cambiar el código otra vez.
   No crear simultáneamente otra copia del mismo conector sin resolver la existente.
6. Pedir `get_kairos_kucoin_ohlcv` de BTCUSDT, interval 1d, limit 90 y comprobar
   status OK, continuidad y último cierre UTC. Un fallo upstream no se soluciona
   repitiendo ni solicitando el snapshot completo.

No se ha desplegado este paquete ni verificado upstream real en esta entrega.

## Herramientas expuestas por este código

- get_kairos_kucoin_service_info: identidad y catálogo esperado; sin upstream.
- get_kairos_kucoin_spot_prices(symbols=None): 12 pares USDT, observación original,
  caché 60s y validación completa. No consulta históricos.
- get_kairos_kucoin_ohlcv(symbol="BTCUSDT",interval="1d",limit=999): diarios cerrados
  UTC, límite 1..1500, caché SQLite incremental. No devuelve semanas del proveedor.
- get_kairos_kucoin_history_snapshot(): actualización conjunta explícita de las 12
  series diarias e indicadores. No refresca Spot y falla sin publicar conjunto parcial.

Las firmas y nombres se conservan. No se modifican cálculo, precios o reglas de
históricos. HYPEUSDT sirve para valoración; macro HYPE/USDC sigue en Hyperliquid.

Caché: KUCOIN_GUARD_DB, default /tmp/kairos-kucoin-guard.sqlite3. Render Free puede
perder ese archivo al reiniciar; no se provisionan discos. Un solo worker mantiene
coordinación local. Guardias 418/429 y Retry-After compartidos, sin reintentos automáticos.

Los consumidores deben convertir campos OHLC de texto a números finitos y adaptar
interval 1d/1D según su contrato antes de usar el agente Estructura y Ciclo.

## Validación local

```bash
python -m unittest discover -v
```

24 pruebas aprobadas: mercado, históricos, catálogo MCP exacto, esquema OHLCV,
despacho de herramientas históricas con datos sintéticos y simulación de los
archivos COPY de Docker. No se construyó una imagen Docker ni se verificó Render.
