# PUBG AFK Helper

[简体中文](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/README.md) · [English](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.en.md) · [日本語](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.ja.md) · [Deutsch](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.de.md) · [Français](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.fr.md) · **Español** · [Português](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.pt.md)

Usa OpenCV para reconocer pantallas de PUBG, mostrar el estado de la detección y ejecutar flujos configurables en Windows. Incluye un modo de vista previa que solo detecta y pruebas de regresión sin conexión.

Python · OpenCV · Windows

[![Windows tests](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml/badge.svg)](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)

Herramienta de proceso automático PUBG basada en reconocimiento de pantalla **OpenCV, entrada de simulación de Windows y detección de cambios de minimapa**.
Identifique el vestíbulo y la interfaz de pago, realice procesos configurables de coincidencia, salto, movimiento, recogida y escape, y muestre el paso actual a través de la ventana de estado superior.

## Función

- La interfaz **reconoce**: lobby, regreso al lobby, confirmación de salida, liquidación de personajes y página de recompensas; Confirmación de reconocimiento continuo y limitación de operaciones repetidas.
- Posicionamiento relativo ****: escale la plantilla y las coordenadas según el tamaño de la pantalla y admita la búsqueda alineada con los bordes para algunos diseños de pantalla panorámica.
- Proceso del juego ****: salto en el tiempo después de que la sala desaparece, gira a la derecha una vez, W+Mayús izquierda para continuar avanzando, haz clic en F para continuar después de mirar hacia abajo.
- **Mini mapa anti-atascado en la pared**: solo compare el terreno del mapa en la esquina inferior derecha y bloquee la marca del personaje central; Pruebe Shift+C primero, luego retroceda y muévase hacia la izquierda y hacia la derecha según los resultados de la detección.
- **Ventana de estado superior**: muestra cuenta regresiva, acciones, motivos de pausa e indicadores de detección de minimapa; La penetración del ratón no roba el foco del juego.
- **configurable y comprobable**: configuración JSON, herramienta de grabación de plantillas, pruebas de regresión fuera de línea, Windows CI.

El programa funciona mediante capturas de pantalla y entradas normales del sistema operativo, no lee la memoria del juego ni inyecta procesos del juego.
El proyecto aún se encuentra en sus primeras etapas; Los horarios fijos y los cambios en el minimapa son aproximados y no pueden confirmar la aeronave, el aterrizaje real, el éxito de la recogida ni el recibo de la recompensa.
Confirme usted mismo las reglas del juego y los riesgos de la cuenta antes de usarlo; Este proyecto no proporciona funciones de derivación anti-trampas.

## inicio rápido

Requiere **Windows 10/11, Python 3.11+**, el juego utiliza el modo de ventana sin bordes del monitor principal.

1. Descargue `PUBG-helper.zip` en la última versión ](https://github.com/chenbinghan666/pubg-afk-helper/releases/latest) de [ o clone este repositorio.
2. Instale Python y marque **Agregue Python a PATH**.
3. Haga doble clic en `install.cmd` y espere a que se complete la instalación de la dependencia.
4. Cuando lo uses por primera vez, haz doble clic en **`preview.cmd`**, vuelve al juego y verifica el registro de reconocimiento; este modo no envía entrada.
5. Después de confirmar que el reconocimiento es correcto, cierre la vista previa y haga doble clic en **`launch.cmd`** para habilitar la operación automática.

```powershell
git clone https://github.com/chenbinghan666/pubg-afk-helper.git
cd pubg-afk-helper
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe bot.py             # Sólo reconocer
.\.venv\Scripts\python.exe bot.py --live      # Habilitar entrada
```

Los clones de Git leen `config.example.json` de forma predeterminada. Cópielo en `config.json` antes de la personalización y la configuración local no se enviará a Git:

```powershell
Copy-Item config.example.json config.json
```

El almacén viene con un conjunto de plantillas de recorte de botones para la interfaz en chino tradicional. Si el idioma, la versión del juego, la escala del HUD o el diseño son diferentes, es necesario volver a grabar la plantilla y no se puede garantizar que sea directamente aplicable a todas las computadoras.

## Proceso predeterminado

```text
Identificar la sala → F comienza a coincidir
  → Desaparición del lobby detectada 3 veces seguidas → espera 120 segundos
  → F Prueba el paracaidismo → girar a la derecha una vez → W + Mayús izquierda
  → 30 segundos después del paracaidismo: mirando al suelo → Toque F cada 0,5 segundos
  → El minimapa es estable durante aproximadamente 1 segundo: intente cruzar, retroceder o atravesar si es necesario
  → Muerte/Asentamiento: Botón de liberación → Regresar al lobby → próxima ronda
```

La desaparición del vestíbulo también puede ser una pantalla de carga, lo que no prueba que hayas entrado en la sala. Todos los tiempos son ajustables.
El desplazamiento predeterminado para giro a la derecha **4050** y el desplazamiento hacia arriba **5000** son sólo parámetros de referencia; El ángulo real depende de la sensibilidad del juego y de la configuración del ratón.
Correr y saltar con Shift+C deben ser coherentes con la tecla del juego y con la configuración de mantener/alternar.

## Teclas de operación

| Botón | función |
| --- | --- |
| **F8** | Pausa únicamente, liberando las teclas retenidas por el script. |
| **F7** | Sólo continúa |
| **F9** | Sal y suelta la llave. |
| **Ctrl+C** | Detener programa en terminal |

La entrada se pausa al salir del juego y se reanudará automáticamente después de volver; la cuenta atrás que ha comenzado todavía se calcula en función del tiempo real transcurrido.
La pausa en la esquina del mouse está desactivada de forma predeterminada para evitar que se pase por alto la protección del disparador y se puede habilitar individualmente con `mouse_corner_pause`.
La limpieza mediante pulsaciones de teclas no se puede realizar cuando el proceso se finaliza a la fuerza o la computadora está apagada.

## Configuración y solución de problemas

Para conocer los parámetros completos, los comandos de grabación de plantillas, el área relativa del minimapa y el método de calibración de sensibilidad, consulte el Manual de configuración y uso de [](../../docs/CONFIGURATION.md).

| pregunta | verificación de prioridad |
| --- | --- |
| Sin reconocimiento ni acción. | Si la ventana superior muestra una pausa, si el juego está en primer plano y si el título de la ventana contiene `PUBG` |
| Fallo en el reconocimiento de inicio o liquidación | Si el idioma de la interfaz, la resolución y la escala HUD coinciden con la plantilla |
| Saltar en paracaídas demasiado pronto/demasiado tarde | `movement.jump_delay_seconds` |
| Levantar demasiado temprano/mirar hacia abajo en la dirección equivocada | Configuración inversa de `pickup_delay_after_jump_seconds`, `look_down_pixels` y eje Y |
| Ángulo de giro a la derecha incorrecto | Calibrar según el ángulo de rotación real `turn_right_pixels` |
| Correr o saltar no tiene ningún efecto. | Combinación de teclas, modo de espera, permisos de ejecución y si el juego acepta entradas analógicas |
| Error de juicio/falta de pared anti-interferencias | Indicadores de escala estables para el área del minimapa, zoom, configuración de rotación y ventanas superiores |

El registro se escribe en el `bot.log` local. Elimine la cuenta, el chat, la ruta privada y otra información antes de enviar comentarios.

## desarrollar

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe package.py
```

La prueba simula la entrada del teclado y el mouse sin operar el juego. La versión pública genera automáticamente imágenes sintéticas para realizar pruebas; si existe localmente
`reference_screens/`, puede utilizar las capturas de pantalla de referencia personal correspondientes para una regresión adicional. Este directorio no está incluido en el paquete de almacén o distribución.
CI ejecuta pruebas en Windows usando Python 3.11 y 3.12.
Las pruebas fuera de línea no pueden reemplazar la verificación real del juego en diferentes hardware, versiones de juego y sensibilidades.

Archivos principales: `bot.py` es la máquina de estado, reconocimiento e implementación de entrada, `status_overlay.py` es la ventana de estado,
`prepare_templates.py` es una herramienta de generación de plantillas de cinco interfaces y `package.py` es un script de creación de paquetes de distribución.

Bienvenido a informar problemas reproducibles a través de [Issues](https://github.com/chenbinghan666/pubg-afk-helper/issues).
Lea las instrucciones de contribución [](../../CONTRIBUTING.md) antes de enviar cambios. Para registros de versión, consulte [CHANGELOG](../../CHANGELOG.md).

## licencia

El código original y la documentación tienen la licencia [MIT License](../../LICENSE). El corte de la interfaz del juego, el nombre y la marca registrada aún pertenecen a sus respectivos titulares de derechos; consulte la declaración de terceros [](../../NOTICE.md) para obtener más detalles. Este proyecto no tiene afiliación ni asociación oficial con KRAFTON/PUBG.
