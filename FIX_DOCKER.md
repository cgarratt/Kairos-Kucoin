Corrección de empaquetado v1.1.0

El Dockerfile ahora copia history_data.py y technical.py además de market_data.py y server.py. Sin cambios funcionales ni de versión.
Validación: 21 pruebas unitarias aprobadas y comprobación de dependencias locales copiadas/importación de históricos. Docker no está disponible en este entorno; arranque real pendiente en Render.

Reemplazar Dockerfile en la ubicación configurada en Render, confirmar que los cuatro .py existan junto a él, guardar commit y desplegar. Luego refrescar el plugin ChatGPT y verificar versión 1.1.0 y cuatro herramientas.
