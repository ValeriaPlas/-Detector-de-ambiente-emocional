"""
OBJETIVO DEL PROGRAMA
--------------------
Este programa realiza una prueba básica de comunicación SPI entre un ESP32
y un dispositivo externo (por ejemplo, una cámara Pixy2).

El objetivo es verificar que el bus SPI esté correctamente configurado y que
exista intercambio de datos entre el maestro (ESP32) y el esclavo (Pixy).
Si se reciben valores variados en la lectura, significa que la comunicación
SPI es funcional.
"""

from machine import SPI, Pin
import time


# =================================================
# 1. CONFIGURACIÓN DE PINES SPI
# =================================================

SCK  = 18   # Reloj SPI
MOSI = 23   # Master Out - Slave In
MISO = 19   # Master In - Slave Out
CS   = 5    # Chip Select (puede cambiarse si falla)
BUS  = 2    # Bus SPI utilizado


# =================================================
# 2. INICIALIZACIÓN DEL BUS SPI
# =================================================

spi = SPI(
    BUS,
    baudrate=1_000_000,   # Velocidad de 1 MHz
    polarity=0,           # Polaridad del reloj
    phase=1,              # Fase del reloj
    sck=Pin(SCK),
    mosi=Pin(MOSI),
    miso=Pin(MISO)
)

# Configuración del pin CS
cs = Pin(CS, Pin.OUT)
cs.value(1)               # CS en alto (dispositivo deseleccionado)

# Pequeña pausa para estabilizar el bus
time.sleep_ms(50)


# =================================================
# 3. PRUEBA DE COMUNICACIÓN SPI
# =================================================

# Buffer para almacenar la respuesta del dispositivo
buf = bytearray(8)

# Activar el dispositivo (CS en bajo)
cs.value(0)

# Enviar 8 bytes (0x00) y leer simultáneamente la respuesta
spi.write_readinto(bytearray(8), buf)

# Desactivar el dispositivo (CS en alto)
cs.value(1)

# Mostrar la respuesta recibida
print("Respuesta raw:", buf)


# =================================================
# 4. INTERPRETACIÓN DE RESULTADOS
# =================================================
# - Si todos los valores son 0x00 o 0xFF constantes,
#   probablemente NO hay comunicación SPI correcta.
# - Si aparecen valores variados, el dispositivo
#   está respondiendo y el bus SPI funciona.
