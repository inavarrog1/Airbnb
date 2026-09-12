# ENTORNO.md — cómo correr esto

Hay **dos entornos** y se comportan distinto. Leer el que corresponde.

---

# A · En tu máquina (Mac o Windows)

Es donde hay que correr los agentes que tocan el portal (`buscador`,
`extractor-de-ficha`), porque la sesión remota los tiene bloqueados por red.

```
python3 -m venv .venv
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
```

**Acá SÍ hay que correr `playwright install`**: tu máquina no trae los navegadores.
En Windows los comandos son `python -m venv .venv`, `.venv\Scripts\pip install
playwright` y `.venv\Scripts\playwright install chromium`.

Y **no** hace falta pasar `executable_path`: Playwright encuentra el navegador que
acaba de instalar.

---

# B · En la sesión remota de Claude Code

## Python y Playwright

```
python3 -m venv .venv
.venv/bin/pip install playwright
```

**No correr `playwright install` acá.** Los navegadores ya están en la máquina, en
`/opt/pw-browsers`.

## La trampa del build de Chromium

El paquete de Playwright que instala `pip` espera un build de Chromium más nuevo
que el que está en la máquina. Si se lanza sin más, falla con:

```
Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1234/...
```

y sugiere correr `playwright install`, que es justo lo que no hay que hacer.

**La solución es apuntar al binario que ya existe:**

```python
b = p.chromium.launch(
    headless=True,
    executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    args=["--no-sandbox", "--disable-dev-shm-usage"],
)
```

Verificar el número de build antes de copiar esta línea — cambia con la imagen:

```
ls /opt/pw-browsers
```

## Red

La sesión remota sale por un proxy con política de egreso. **`portalinmobiliario.com`
está habilitado** (se verificó el 2026-09-12: el CONNECT pasa y el portal responde
200). Antes estaba denegado con 403; si vuelve a estarlo, el diagnóstico es:

```
curl -sS "$HTTPS_PROXY/__agentproxy/status"
```

Nunca desactivar la verificación de TLS ni sacar `HTTPS_PROXY`. Una denegación de
política no se reintenta: se reporta.

## Lo que sigue sin poder correr desde acá: el navegador

Que la red llegue no alcanza. **El motor de Chromium no atraviesa el proxy de
egreso**: toda navegación muere con `net::ERR_CONNECTION_RESET`, y el estado del proxy
lo registra como `ws_closed_mid_exchange` — el túnel se corta a mitad del intercambio.
Se probó con y sin `proxy=` explícito, con UA de navegador, con HTTP/2 deshabilitado y
bloqueando todos los subrecursos. Siempre igual.

Lo que **sí** funciona desde la sesión remota:

| Cliente | Resultado |
|---|---|
| `curl` con UA de navegador | 200 |
| `APIRequestContext` de Playwright (stack HTTP, no el motor) | 200 |
| `chromium.launch()` + `page.goto()` | `ERR_CONNECTION_RESET` |

Chromium **arranca** bien y renderiza: sirve para verificar selectores contra HTML ya
traído (`page.route(...).fulfill(...)`). Lo que no hace es ir a buscarlo él.

Conclusión práctica: el `buscador` (item 03) y el `extractor-de-ficha` (item 09)
siguen siendo trabajo de la máquina local — pero por el navegador, no por la red.
