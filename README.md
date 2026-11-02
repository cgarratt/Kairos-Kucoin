# Kairos KuCoin MCP 1.1.0

Datos públicos Spot e históricos diarios; sin claves de cuenta, órdenes, saldos ni procesos programados.

## Actualizar el servicio existente

Reemplazar el contenido del repositorio por la carpeta kairos-kucoin-connector descomprimida. Mantener la Root Directory de Render coherente con la ubicación de Dockerfile. Conservar el endpoint HTTPS /mcp, variables y configuración existentes. No crear otro servicio. Docker ejecuta python server.py, PORT de Render o10000.

## Herramientas

- get_kairos_kucoin_service_info: versión 1.1.0 y alcance, sin consultar exchange.
- get_kairos_kucoin_spot_prices:12 pares USDT, caché 60s, observación original, precios positivos y cobertura completa.
- get_kairos_kucoin_ohlcv(symbol=BTCUSDT,interval=1d,limit=999): velas cerradas UTC; límite1..1500. Ventana999d por defecto. No devuelve velas1W del proveedor: semanas se construyen desde los días en consumidores.
- get_kairos_kucoin_history_snapshot:12 series diarias completas disponibles y sus indicadores. No consulta Spot. Un fallo de cualquier token devuelve DATA_ERROR sin publicar un conjunto histórico parcial, identificando failed_symbol.

Cada vela conserva O/H/L/C/volumen/turnover y fechasUTC. Se ordenan, excluye el día abierto y se rechazan duplicados, OHLC inválido y huecos internos. Historia más corta desde el listado se declara mediante count, coverage_start_utc y coverage_complete; no se fabrican días previos. Una serie debe llegar hasta el último día cerrado.

Caché SQLite por par, con rangos cubiertos: llamadas repetidas al mismo cierre no consultan exchange; al siguiente día se solicitan sólo días faltantes. Al ampliar una ventana puede requerirse una petición completa. Guardias418/429 comparten pausa con Spot y respetan Retry-After/reset. No hay reintentos automáticos. Las peticiones concurrentes de la misma vela comparten la descarga.

KUCOIN_GUARD_DB controla el archivo compartido de velas y pausas, default /tmp/kairos-kucoin-guard.sqlite3. Render Free puede perderlo al suspender/reiniciar/desplegar. Utilizar ruta de disco persistente sólo si ya está provisionado; este paquete no crea ni contrata discos. Conservar un worker para coordinación local.

RSI14 Wilder, mediaRSI14, StochRSI14/14/3/3, EMA20/50/100/200. Si el listado es demasiado reciente para un indicador, queda N/D, sin sustituirlo con datos de Binance. HYPEUSDT es sólo valoración; el macro HYPE/USDC sigue en Hyperliquid.

22 pruebas aprobadas y discovery/protocolo MCP comprobado localmente con datos sintéticos para 12series. No se declara cobertura histórica en vivo: este entorno recibió respuestasREST no JSON; validar desde Render después de desplegar. Ver get_kairos_kucoin_history_snapshot: status OK,12series, fechas hasta último cierre UTC. Si falla, revisar failed_symbol/reason sin repetir durante una pausa.

API oficial: https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-klines
