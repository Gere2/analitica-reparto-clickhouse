# Compartir Delivery Atlas en Vercel

## Arquitectura de esta demo

```text
Navegador del compañero -> web y función GET en Vercel
                       -> HTTPS temporal de Cloudflare
                       -> gateway de lectura autenticado
                       -> API Atlas local -> ClickHouse local
```

La generación de eventos, SQLite y ClickHouse permanecen en Docker en el ordenador de Jere. La web compartida representa sus consultas; no reproduce posiciones inventadas por separado. Si el ordenador se duerme, Docker se detiene o el túnel se cierra, la web permanece publicada pero los datos dejan de actualizarse y se muestra un aviso.

La web es visible para quien tenga su enlace. Vercel y Cloudflare transportan posiciones y pedidos **ficticios**, recuentos y datos del catálogo público. No se publican los archivos masivos ni los recursos del profesor. El token del gateway solo existe en un archivo local ignorado y en una variable de entorno sensible de la función; nunca se incluye en el JavaScript del navegador.

## Qué puede leer

`simulation`, `operations`, `status`, `track`, `summary` (Madrid), `inventory` y `catalog`. El gateway valida rutas y parámetros, rechaza POST/PUT/PATCH/DELETE y requiere un token. `status` y `simulation` se reducen a campos necesarios del panel. La función de Vercel también rechaza escrituras. El panel compartido no tiene controles de simulación ni botón de inserción. El acceso al SQL de ClickHouse continúa local.

Hay una caché en el gateway: 1,5 s para seguimiento/estado, 10 s para navegación y 60 s para catálogo/inventario, con un máximo de 128 claves. Agrupa consultas de varios espectadores; añade demora respecto al panel local. El intervalo visual sigue sin ser una garantía de latencia.

## Preparar y arrancar

1. Arrancar Atlas siguiendo [DEMO-TRACKING.md](DEMO-TRACKING.md). Iniciar la flota desde http://127.0.0.1:8001/.
2. Crear un token y los archivos locales sin imprimirlo:

```bash
python3 - <<'PY'
from pathlib import Path
import secrets
p = Path('data/sharing'); p.mkdir(parents=True, exist_ok=True)
token = p / 'token'
if not token.exists():
    token.write_text(secrets.token_hex(32)); token.chmod(0o600)
env = p / 'gateway.env'
env.write_text('ATLAS_SHARE_TOKEN=' + token.read_text().strip() + '\n')
env.chmod(0o600)
PY
docker compose -f compose.yaml -f compose.share.yaml --profile atlas up -d --build --no-deps share-gateway share-tunnel
docker compose -f compose.yaml -f compose.share.yaml logs share-tunnel
```

3. Copiar la URL `https://….trycloudflare.com` del registro a `data/sharing/origin` (no es una contraseña). [Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) genera una URL temporal que cambia al crear otro túnel; no tiene garantía de disponibilidad. No requiere cuenta de Cloudflare.
4. Con Vercel CLI autenticado, enlazar **el proyecto de la demo** y configurar sus variables de producción:

```bash
vercel link --project delivery-atlas-demo --scope contrerasgeremi-gmailcoms-projects --yes
vercel env add ATLAS_SHARE_TOKEN production --sensitive --yes < data/sharing/token
vercel env add ATLAS_SHARE_ORIGIN production --yes < data/sharing/origin
vercel deploy --prod --scope contrerasgeremi-gmailcoms-projects --yes
```

Usar `--force` en `env add` al sustituir una variable ya configurada, y volver a desplegar. No pasar tokens por argumentos ni escribirlos en Git. `scripts/build_shared.mjs` prepara los tres archivos del dashboard; `.vercelignore` limita la subida al frontend, función y configuración.

Vercel aloja la web y una función por petición. El proceso permanente y el almacenamiento del laboratorio quedan fuera de las [funciones de duración limitada](https://vercel.com/docs/functions/limitations).

## Parar la compartición

```bash
docker compose -f compose.yaml -f compose.share.yaml stop share-tunnel share-gateway
```

Esto no borra datos ni detiene ClickHouse o la demo local. Para abrir otra sesión, comprobar la URL actual del túnel, actualizar `ATLAS_SHARE_ORIGIN` si cambia y desplegar de nuevo. No se ha configurado arranque automático del túnel ni del simulador al reiniciar el ordenador.
