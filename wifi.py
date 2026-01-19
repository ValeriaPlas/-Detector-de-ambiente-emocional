"""
OBJETIVO DEL MÓDULO
------------------
Este módulo proporciona una función sencilla y reutilizable para conectar
un dispositivo (como un ESP32) a una red Wi-Fi utilizando MicroPython.

La función maneja la activación de la interfaz de red, el intento de conexión
y un control de tiempo de espera (timeout) para evitar que el programa quede
bloqueado indefinidamente si la red no está disponible.
"""

import network
import time


def conectar(ssid, password, timeout=15):
    """
    Conecta el dispositivo a una red Wi-Fi.

    Parámetros:
    - ssid: Nombre de la red Wi-Fi
    - password: Contraseña de la red Wi-Fi
    - timeout: Tiempo máximo (en segundos) para intentar la conexión

    Retorna:
    - Configuración de red del dispositivo (IP, máscara, gateway, DNS)

    Lanza:
    - OSError si no se logra la conexión dentro del tiempo establecido
    """
    # Crear la interfaz Wi-Fi en modo estación
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Intentar conexión solo si aún no está conectado
    if not wlan.isconnected():
        wlan.connect(ssid, password)
        t0 = time.time()

        # Esperar hasta conectar o hasta que se cumpla el timeout
        while not wlan.isconnected():
            if time.time() - t0 > timeout:
                raise OSError("Timeout conectando a WiFi")
            time.sleep(0.5)

    # Retornar información de red (IP, máscara, gateway, DNS)
    return wlan.ifconfig()
