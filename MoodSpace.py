"""
OBJETIVO DEL CÓDIGO
------------------
Este programa implementa un sistema llamado "MoodSpace Kinetic" utilizando un
ESP32 y una cámara Pixy2 para medir el nivel de movimiento dentro de un espacio
(por ejemplo, un aula).

El sistema detecta el movimiento de un objeto mediante visión artificial,
calcula un nivel de "caos" o agitación basado en la intensidad del movimiento
y muestra esta información en tiempo real a través de una página web alojada
directamente en el ESP32.

La interfaz web se actualiza automáticamente usando JavaScript y permite
visualizar el nivel de caos, una etiqueta de estado (Zen, Activo o Caos) y la
posición del objeto detectado.
"""

import network
import socket
import time
import machine
import pixy      # Driver de la Pixy2 (práctica anterior)
import gc


# =================================================
# 1. CONFIGURACIÓN DE LA RED WIFI
# =================================================

SSID = 'Totalplay-D6AB'
PASSWORD = 'D6ABD710EAAMeU3q'

def conectar_wifi():
    """
    Conecta el ESP32 a una red Wi-Fi.

    Retorna:
    - Dirección IP asignada al ESP32
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print('Conectando a WiFi...')
        wlan.config(dhcp_hostname="MoodSpace-ESP32")
        wlan.connect(SSID, PASSWORD)

        intentos = 0
        while not wlan.isconnected():
            time.sleep(1)
            print('.', end='')
            intentos += 1
            if intentos > 20:
                break

    print('\n¡Conectado! Entra a: http://' + wlan.ifconfig()[0])
    return wlan.ifconfig()[0]


# =================================================
# 2. CONFIGURACIÓN DE LA CÁMARA PIXY (I2C)
# =================================================

# Inicialización del bus I2C
i2c = machine.I2C(
    0,
    scl=machine.Pin(22),
    sda=machine.Pin(21),
    freq=100000
)

# Crear objeto Pixy2
camara = pixy.Pixy2(i2c)


# =================================================
# 3. VARIABLES GLOBALES DEL SISTEMA
# =================================================
# Estas variables representan el estado actual del sistema
# y son consultadas por la página web

estado_sistema = {
    "nivel_caos": 0,     # Valor entre 0 y 100
    "etiqueta": "Zen",   # Estado cualitativo
    "x_obj": 0,          # Posición X del objeto
    "y_obj": 0           # Posición Y del objeto
}


# =================================================
# 4. PÁGINA WEB (HTML + CSS + JAVASCRIPT)
# =================================================
# El ESP32 actúa como servidor web y envía esta página al navegador.
# JavaScript consulta los datos cada 500 ms usando fetch().

html_page = """<!DOCTYPE html>
<html>
<head>
 <title>MoodSpace Monitor</title>
 <meta name="viewport" content="width=device-width, initial-scale=1">
 <style>
   body { font-family: sans-serif; text-align: center; background: #1a1a1a; color: white; }
   .container { margin-top: 50px; }
   .meter { width: 80%; height: 30px; background: #444; margin: 20px auto; border-radius: 15px; overflow: hidden; }
   .fill { height: 100%; width: 0%; background: #00ff00; transition: width 0.5s, background 0.5s; }
   h1 { font-size: 2.5rem; }
   #valor { font-size: 4rem; font-weight: bold; }
   #estado { font-size: 1.5rem; color: #aaa; }
 </style>
</head>
<body>
 <div class="container">
   <h1>MoodSpace Kinetic</h1>
   <p>Nivel de Agitacion del Aula</p>

   <div class="meter"><div id="barra" class="fill"></div></div>

   <div id="valor">0%</div>
   <div id="estado">Esperando datos...</div>
   <p>Posicion Detectada: X:<span id="posx">0</span> Y:<span id="posy">0</span></p>
 </div>

 <script>
   setInterval(function() {
     fetch('/data')
       .then(response => response.json())
       .then(data => {
         document.getElementById("valor").innerText = data.caos + "%";
         document.getElementById("estado").innerText = data.etiqueta;
         document.getElementById("posx").innerText = data.x;
         document.getElementById("posy").innerText = data.y;

         let barra = document.getElementById("barra");
         barra.style.width = data.caos + "%";

         if(data.caos < 30) barra.style.background = "#00ff00";
         else if(data.caos < 70) barra.style.background = "#ffff00";
         else barra.style.background = "#ff0000";
       });
   }, 500);
 </script>
</body>
</html>
"""


# =================================================
# 5. LÓGICA DEL SENSOR Y CÁLCULO DEL CAOS
# =================================================

x_anterior = 0
y_anterior = 0
caos_acumulado = 0

def actualizar_sensor():
    """
    Lee los datos de la Pixy, calcula el movimiento del objeto
    y actualiza el nivel de caos del sistema.
    """
    global x_anterior, y_anterior, caos_acumulado

    bloques = camara.get_blocks(1, 1)
    movimiento = 0
    detectado = False

    if len(bloques) > 0:
        detectado = True
        obj = bloques[0]

        estado_sistema["x_obj"] = obj['x']
        estado_sistema["y_obj"] = obj['y']

        if x_anterior != 0 and y_anterior != 0:
            dx = abs(obj['x'] - x_anterior)
            dy = abs(obj['y'] - y_anterior)
            movimiento = dx + dy

        x_anterior = obj['x']
        y_anterior = obj['y']
    else:
        x_anterior = 0
        y_anterior = 0

    if movimiento > 3:
        caos_acumulado += movimiento / 2
    else:
        caos_acumulado -= 1.5

    if caos_acumulado > 100: caos_acumulado = 100
    if caos_acumulado < 0: caos_acumulado = 0

    print(f"Mov: {movimiento} | Caos: {int(caos_acumulado)}% | Obj: {detectado}")

    estado_sistema["nivel_caos"] = int(caos_acumulado)

    if caos_acumulado < 30:
        estado_sistema["etiqueta"] = "Zen"
    elif caos_acumulado < 70:
        estado_sistema["etiqueta"] = "Activo"
    else:
        estado_sistema["etiqueta"] = "!!! CAOS !!!"


# =================================================
# 6. BUCLE PRINCIPAL (SERVIDOR + SENSOR)
# =================================================

ip = conectar_wifi()

# Crear servidor web
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)
s.setblocking(False)

print("Sistema MoodSpace Iniciado.")

while True:
    actualizar_sensor()

    try:
        conn, addr = s.accept()
        request = str(conn.recv(1024))

        if 'GET /data' in request:
            json_response = '{"caos": %s, "etiqueta": "%s", "x": %s, "y": %s}' % (
                estado_sistema["nivel_caos"],
                estado_sistema["etiqueta"],
                estado_sistema["x_obj"],
                estado_sistema["y_obj"]
            )
            header = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n'
            conn.send(header + json_response)
        else:
            header = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'
            conn.send(header + html_page)

        conn.close()

    except OSError:
        pass
    except Exception as e:
        print("Error web:", e)

    time.sleep(0.05)
