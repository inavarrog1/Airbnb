# ENTORNO.md — cómo correr esto

## Python y Playwright

```
python3 -m venv .venv
.venv/bin/pip install playwright
```

**No correr `playwright install`.** Los navegadores ya están en la máquina, en
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
está denegado** (403 en el CONNECT), así que el `buscador` y el `extractor-de-ficha`
no pueden correr desde acá.

Diagnóstico:

```
curl -sS "$HTTPS_PROXY/__agentproxy/status"
```

Nunca desactivar la verificación de TLS ni sacar `HTTPS_PROXY`. Una denegación de
política no se reintenta: se reporta.
