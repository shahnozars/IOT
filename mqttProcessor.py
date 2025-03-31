import paho.mqtt.client as mqtt

broker = "test.mosquitto.org"
port = 1883
subscribe_topic = "iot/device/sensor"
response_topic = "iot/device/response"
mode_topic = "iot/device/mode"
current_mode = "Manual"


def on_message(client, userdata, msg):
    try:
        sensor_value = float(msg.payload.decode())
        print(f"Получено значение датчика: {sensor_value}")

        if sensor_value > 90:
            response = "off"
        elif sensor_value < 60:
            response = "on"
        else:
            response = None

        if response and current_mode == "Manual":
            client.publish(response_topic, response)
            print(f"Отправлена команда: {response}")

    except ValueError:
        print("Некорректное значение датчика.")


def switch_mode(client, new_mode):
    global current_mode
    if new_mode in ["Manual", "Automatic"]:
        current_mode = new_mode
        client.publish(mode_topic, new_mode)
        print(f"Режим изменён на: {new_mode}")


def simulate_mode_switching():
    while True:
        switch_mode(client, "Manual")
        time.sleep(20)
        switch_mode(client, "Automatic")
        time.sleep(20)


client = mqtt.Client()
client.on_connect = lambda c, u, f, rc: c.subscribe(subscribe_topic)
client.on_message = on_message

client.connect(broker, port)
import threading
import time

threading.Thread(target=simulate_mode_switching, daemon=True).start()
client.loop_forever()
