import network
import socket
import time
import machine
import pixy # Tu driver de la practica anterior
import gc

# --- 1. CONFIGURACIÓN WIFI ---
SSID = 'Totalplay-D6AB' 
PASSWORD = 'D6ABD710EAAMeU3q'

def conectar_wifi():
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
            if intentos > 20: break
    print('\n¡Conectado! Entra a: http://' + wlan.ifconfig()[0])
    return wlan.ifconfig()[0]

# --- 2. CONFIGURACIÓN PIXY (I2C) ---
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=100000)
camara = pixy.Pixy2(i2c)

# --- 3. VARIABLES GLOBALES DE ESTADO ---
# Estas variables guardan el estado actual para que la web lo lea
estado_sistema = {
    "nivel_caos": 0,    # 0 a 100
    "etiqueta": "Zen",  # Zen, Activo, Caos
    "x_obj": 0,
    "y_obj": 0
}

# --- 4. LA PÁGINA WEB (HTML + JAVASCRIPT) ---
# Guardamos el HTML dentro de una variable de texto.
# El JavaScript interno (fetch) es el truco para que se actualice sola.
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
   // Esta funcion pide datos al ESP32 cada 500ms
   setInterval(function() {
     fetch('/data') // Pide el JSON
       .then(response => response.json())
       .then(data => {
         // Actualizar textos
         document.getElementById("valor").innerText = data.caos + "%";
         document.getElementById("estado").innerText = data.etiqueta;
         document.getElementById("posx").innerText = data.x;
         document.getElementById("posy").innerText = data.y;
         
         // Actualizar barra y color
         let barra = document.getElementById("barra");
         barra.style.width = data.caos + "%";
         
         // Cambiar color segun intensidad
         if(data.caos < 30) barra.style.background = "#00ff00"; // Verde
         else if(data.caos < 70) barra.style.background = "#ffff00"; // Amarillo
         else barra.style.background = "#ff0000"; // Rojo
       })
       .catch(err => console.log(err));
   }, 500); // 500 milisegundos = 0.5 segundos
 </script>
</body>
</html>
"""

# --- 5. LÓGICA DE SENSOR (Matemáticas) ---
x_anterior = 0
y_anterior = 0
caos_acumulado = 0

def actualizar_sensor():
    global x_anterior, y_anterior, caos_acumulado
    
    bloques = camara.get_blocks(1, 1) 
    
    movimiento = 0
    detectado = False
    
    if len(bloques) > 0:
        detectado = True
        obj = bloques[0]
        
        # Actualizar datos para la web
        estado_sistema["x_obj"] = obj['x']
        estado_sistema["y_obj"] = obj['y']
        
        # Calcular movimiento solo si el objeto ya estaba en pantalla antes
        # (Evita saltos locos cuando el objeto entra por primera vez)
        if x_anterior != 0 and y_anterior != 0:
            dx = abs(obj['x'] - x_anterior)
            dy = abs(obj['y'] - y_anterior)
            movimiento = dx + dy
        
        # Actualizar referencias
        x_anterior = obj['x']
        y_anterior = obj['y']
    else:
        # Si no ve nada, reseteamos referencias para no tener "falsos saltos"
        x_anterior = 0
        y_anterior = 0

    # --- LÓGICA DE SENSIBILIDAD AJUSTADA ---
    
    # UMBRAL: Antes era 15, ahora es 3 (Detecta movimientos sutiles)
    if movimiento > 3: 
        # Si te mueves mucho, suma mas. Si te mueves poco, suma poco.
        plus = movimiento / 2  
        caos_acumulado += plus
    else:
        # Si estas quieto, baja el caos gradualmente
        caos_acumulado -= 1.5 
        
    # Limites (Clamp 0-100)
    if caos_acumulado > 100: caos_acumulado = 100
    if caos_acumulado < 0: caos_acumulado = 0
    
    # Debug en consola (Vital para calibrar)
    print(f"Mov: {movimiento} | Caos: {int(caos_acumulado)}% | Obj: {detectado}")
    
    # Actualizar estado global
    estado_sistema["nivel_caos"] = int(caos_acumulado)
    
    if caos_acumulado < 30: estado_sistema["etiqueta"] = "Zen"
    elif caos_acumulado < 70: estado_sistema["etiqueta"] = "Activo"
    else: estado_sistema["etiqueta"] = "!!! CAOS !!!"

# --- 6. BUCLE PRINCIPAL (SERVIDOR + SENSOR) ---
ip = conectar_wifi()

# Crear socket servidor
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)
s.setblocking(False) # IMPORTANTE: Modo No-Bloqueante para que la camara siga funcionando

print("Sistema MoodSpace Iniciado.")

while True:
    # A. Actualizamos el sensor (Siempre corre)
    actualizar_sensor()
    
    # B. Atendemos peticiones Web (Si las hay)
    try:
        conn, addr = s.accept() # Intentar aceptar conexion
        # Si nadie llama, esto da error en modo no-bloqueante y salta al except (pass)
        
        request = str(conn.recv(1024))
        
        # Analizar qué pide el navegador
        if 'GET /data' in request:
            # Pide DATOS JSON (JavaScript)
            json_response = '{"caos": %s, "etiqueta": "%s", "x": %s, "y": %s}' % (
                estado_sistema["nivel_caos"],
                estado_sistema["etiqueta"],
                estado_sistema["x_obj"],
                estado_sistema["y_obj"]
            )
            header = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n'
            conn.send(header + json_response)
            
        else:
            # Pide la PÁGINA NORMAL (HTML)
            header = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'
            conn.send(header + html_page)
            
        conn.close()
        
    except OSError:
        # No hay nadie conectándose, seguimos con la cámara
        pass
        
    except Exception as e:
        print("Error web:", e)
    
    # Pequeña pausa para estabilidad
    time.sleep(0.05)