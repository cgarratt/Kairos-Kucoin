# MCP_KuCoin v1.0.1 · Suite 2026.11.02.1

Release coordinado con Web3.0.33 y GPT1.3.16. Herramienta local de versión: get_kairos_kucoin_service_info(). No hace consultas de mercado. El resto de herramientas y sus alcances se conservan. Revisar INSTALACION_SUITE.md del paquete completo. Preparado localmente; no desplegado ni certificado contra el servidor remoto.

# Kairos KuCoin MCP v1.0.0 · Spot de respaldo

Servicio de datos públicos, sin acceso a cuenta, API keys, órdenes, retiros ni transferencias. Una llamada HTTP GET https://api.kucoin.com/api/v1/market/allTickers obtiene el lote de tickers; solo devuelve los 12 pares Kairos: BTC, ETH, SOL, LINK, HYPE, HBAR, SUI, ONDO, PUMP, PLUME, PEPE y VIRTUAL, cotizados en USDT.

Herramienta MCP: get_kairos_kucoin_spot_prices(symbols=None). symbols opcional es una lista de pares canónicos como BTCUSDT. Los símbolos del proveedor usan BTC-USDT; se preservan exchange_symbol, source=KuCoin Spot, provider=KUCOIN y as_observed_utc de la respuesta KuCoin, sin sustituir esa fecha al leer caché.

Los 12 pares deben existir con precios y bid/ask positivos, finitos y sin cruce. Rechaza respuestas incompletas, duplicados o timestamp >180s de antigüedad / >30s futuro. El timestamp corresponde a la instantánea global allTickers, no al último trade de cada activo. No es una instantánea atómica de operaciones ni garantiza precio de ejecución.

Caché compartida60s por proceso. Un lock agrupa solicitudes concurrentes. Sin trabajos periódicos ni reintentos automáticos. HTTP429/418 y código KuCoin429000 activan pausa; se respeta Retry-After y gw-ratelimit-reset (milisegundos). SQLite conserva la pausa mientras sobreviva el archivo KUCOIN_GUARD_DB; valor predeterminado /tmp/kairos-kucoin-guard.sqlite3. Render Free puede perder ese archivo al recrear el servicio. Un worker.

## Despliegue en GitHub y Render

1. Crear un repositorio GitHub Kairos-KuCoin o una carpeta kairos-kucoin-connector en un repositorio existente. Subir el CONTENIDO DESCOMPRIMIDO de esta carpeta, incluidos server.py, market_data.py, requirements.txt y Dockerfile.
2. Render → New → Web Service → conectar el repositorio. Runtime: Docker. Root Directory: kairos-kucoin-connector si se subió la carpeta; dejar vacío si sus archivos están en la raíz. Nombre sugerido kairos-kucoin. No hay comando de build/start manual: Dockerfile lo define. Plan Free compatible, con posibles arranques lentos tras inactividad. Conservar el puerto PORT de Render (10000 por defecto).
3. Al desplegar, tomar la URL HTTPS que Render muestre y agregar /mcp. Ejemplo ilustrativo, NO provisionado: https://TU-SERVICIO.onrender.com/mcp.
4. Conectar ese endpoint como nuevo MCP de KairosGPT/ChatGPT. El servicio publicado por este paquete es público y solo de lectura; cualquier restricción de acceso adicional requiere configuración en el alojamiento/proxy compatible con el cliente.
5. Verificar discovery de get_kairos_kucoin_spot_prices y una invocación con status OK, source KuCoin Spot,12 registros y timestamp vigente. Si un par no está listado o el proveedor falla, el resultado correcto es DATA_ERROR: no se inventa el activo ni se cambia a otro token.

## Activación en KairosWeb

Instalar el paquete compañero KairosWeb v3.0.32 en el repositorio Web habitual. En Render Web agregar KUCOIN_MCP_URL con la URL real /mcp y volver a desplegar. No requiere API keys de KuCoin. BINANCE_MCP_URL permanece configurado al MCP Binance v5.4.0.

Solo Actualizar Spot solicita datos. Primero Binance; si el primario tiene timeout/conexión, HTTP418/429 o HTTP500/502/503/504, se intenta KuCoin una vez. Si Binance está en pausa local, se omite su llamada y se consulta el respaldo. Cada valoración usa un proveedor completo; no se rellenan huecos con precios Binance antiguos. Si ambos fallan, no se publica valoración ni se vuelve vigente la observación anterior. Errores de autorización, configuración o esquema no disparan respaldo automático. El tiempo por MCP se limita a45s cuando el respaldo está configurado.

La Web identifica KuCoin como respaldo en Portafolio, etiqueta Spot y metadatos /api/market-status y /api/portfolio. Los históricos/ciclos/BSI de Binance NO se sustituyen por velas KuCoin. Tras una carga de respaldo no hay nuevos históricos: modos que necesiten esos datos pueden permanecer N/D; cálculos con anclas publicadas pueden seguir su política. HYPE macro sigue en Hyperliquid HYPE/USDC. Valorar HYPE en USDT no convierte ingresos USDC en USDT ni cambia custodia/venue real.

Al siguiente clic se intenta Binance nuevamente si su pausa venció. No hay sondeo ni retorno automático. Alertas :15 no se modifica por instalar la Web; para que la tarea/GPT utilicen este MCP, conectar la herramienta y aplicar la política siguiente.

## Adenda para KairosGPT y Alertas (tras conectar el MCP)

Autorización del usuario02/11/2026: KuCoin Spot es respaldo de valoración cuando Binance falla por timeout, conexión o restricción418/429. Hacer una sola consulta conjunta de los12 activos. Durante una pausa Binance conocida y vigente, omitir Binance y consultar KuCoin. No hacer reintentos repetitivos. Exigir fuente,12 precios positivos y observación con antigüedad≤180s/futuro≤30s. Mostrar proveedor/hora y marcar RESPALDO KUCOIN; no afirmar que son cotizaciones Binance. Usar solo un proveedor de precios por corrida. No mezclar velas, recalcular pivotes aprobados ni certificar BSI Binance con cierres KuCoin. El resto de reglas financieras/MASTER permanece vigente. Si KuCoin falla o falta un par, DATA_ERROR sin valorar parcialmente. Alertas solo avisa objetivos alcanzados y conserva su horario :15; nunca envía órdenes ni convierte propuestas en fills.

## Verificación

10 pruebas unitarias del conector: lote/caché, cobertura, timestamps, cotizaciones inválidas, duplicados, cuotas persistentes, errores de red y símbolos. Discovery e invocación MCP comprobados en proceso con datos sintéticos. Web:172 pruebas Python y10 comprobaciones JavaScript. No se construyó imagen Docker real ni se desplegó en GitHub/Render. El intento HTTP real desde el entorno de desarrollo no produjo JSON válido; cobertura real de los12 pares y latencia deben verificarse desde el servicio desplegado.

Fuentes técnicas oficiales:
- https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-all-tickers
- https://www.kucoin.com/docs-new/rate-limit-rule-classic
