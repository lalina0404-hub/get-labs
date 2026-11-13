import time
import RPi.GPIO as GPIO
import spidev
import numpy as np
import matplotlib.pyplot as plt


########################################
# Settings
########################################

threshold = 20      # trigger level: deviation of mic 0 from background, ADC codes
timeout_ms = 15000  # how long Pico waits for a clap
SPI_CS = 8


########################################
# Setting up SPI device and CS pin
########################################

spi = spidev.SpiDev()
spi.open(0, 0)
spi.mode = 0
spi.max_speed_hz = 10000
spi.no_cs = True    # CS is controlled manually

GPIO.setmode(GPIO.BCM)
GPIO.setup(SPI_CS, GPIO.OUT)


########################################
# Reading one answer from Pico
# Answer: "SND2", length (4 bytes), CRC (4 bytes), data
########################################

def read_answer():
    start = b""
    while start != b"SND2":
        start = (start + bytes(spi.xfer2([0])))[-4:]

    header = bytes(spi.xfer2([0] * 8))
    size = int.from_bytes(header[:4], "little")

    data = bytearray()
    while len(data) < size:
        data.extend(spi.xfer2([0] * min(64, size - len(data))))
    return bytes(data)


########################################
# Actual measuring script
########################################

try:
    # Reset previous exchange and select Pico
    GPIO.output(SPI_CS, 1)
    time.sleep(0.06)
    GPIO.output(SPI_CS, 0)

    # Command to Pico: wait for a clap and record
    spi.xfer2(list(f"capture {threshold} {timeout_ms}\n".encode()))
    print(read_answer().decode())
    print("Clap now!")

    # Pico sends text line with settings, then samples: mic 0, mic 1, mic 0, ...
    answer = read_answer()
    header, _, payload = answer.partition(b"\n")
    print(header.decode())

    samples = np.frombuffer(payload, dtype="<u2").reshape(-1, 2)
    data_0 = samples[:, 0]
    data_1 = samples[:, 1]

    # Saving and showing samples
    np.savetxt("data_0.txt", data_0, fmt="%d")
    np.savetxt("data_1.txt", data_1, fmt="%d")

    plt.plot(data_0)  # blue
    plt.plot(data_1)  # orange
    plt.show()

finally:
    GPIO.output(SPI_CS, 1)
    GPIO.cleanup()
    spi.close()
