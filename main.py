import tkinter as tk
from tkinter import ttk
import time
import threading
import random
import paho.mqtt.client as mqtt


class IoTDeviceSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Симулятор IoT-устройства")
        self.root.geometry("400x500")
        self.root.resizable(False, False)

        self.mode = "Ручной"
        self.sensor_value = 50
        self.pump_status = False
        self.running = True
        self.update_period = 3
        self.critical_low = 30
        self.critical_high = 70

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect("test.mosquitto.org", 1883, 60)
        threading.Thread(target=self.mqtt_client.loop_forever, daemon=True).start()

        self.create_ui()
        threading.Thread(target=self.sensor_update_loop, daemon=True).start()

    def validate_positive(self, value):
        if value.isdigit():
            return True
        return False

    def configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#F0F0F0')
        self.style.configure('TLabel', background='#F0F0F0', font=('Helvetica', 10))
        self.style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'), foreground='#2C3E50')
        self.style.configure('TButton', font=('Helvetica', 10), relief='flat')
        self.style.configure('Green.TButton', background='#2ECC71', foreground='white')
        self.style.configure('Red.TButton', background='#E74C3C', foreground='white')
        self.style.configure('TCombobox', padding=5)
        self.style.configure('Horizontal.TProgressbar', thickness=20, troughcolor='#ECF0F1', background='#3498DB')

    def create_ui(self):
        self.configure_styles()
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Блок управления режимом
        mode_frame = ttk.LabelFrame(main_frame, text=" Режим работы ", padding=10)
        mode_frame.grid(row=0, column=0, padx=10, pady=5, sticky='ew')

        self.mode_selector = ttk.Combobox(
            mode_frame,
            values=["Ручной", "Автоматический"],
            state="readonly",
            width=15
        )
        self.mode_selector.set(self.mode)
        self.mode_selector.pack(side='left')
        self.mode_selector.bind("<<ComboboxSelected>>", self.change_mode)

        # Блок показаний датчика
        sensor_frame = ttk.LabelFrame(main_frame, text=" Показания датчика ", padding=10)
        sensor_frame.grid(row=1, column=0, padx=10, pady=5, sticky='ew')

        self.sensor_progress = ttk.Progressbar(
            sensor_frame,
            orient='horizontal',
            length=200,
            mode='determinate',
            style='Horizontal.TProgressbar'
        )
        self.sensor_progress.pack(pady=5)
        self.sensor_progress['value'] = self.sensor_value

        self.sensor_label = ttk.Label(
            sensor_frame,
            text=f"{self.sensor_value}%",
            font=('Helvetica', 14, 'bold'),
            foreground='#2C3E50'
        )
        self.sensor_label.pack()

        # Блок управления насосом
        pump_frame = ttk.LabelFrame(main_frame, text=" Управление насосом ", padding=10)
        pump_frame.grid(row=2, column=0, padx=10, pady=5, sticky='ew')

        self.pump_button = ttk.Button(
            pump_frame,
            text="▶ Запустить насос",
            style='Green.TButton',
            command=self.toggle_pump
        )
        self.pump_button.pack(side='left', padx=5)

        self.pump_status_label = ttk.Label(
            pump_frame,
            text="Статус: Выключен",
            foreground='#E74C3C',
            font=('Helvetica', 10, 'bold')
        )
        self.pump_status_label.pack(side='left', padx=15)

        # Блок настроек
        settings_frame = ttk.LabelFrame(main_frame, text=" Настройки ", padding=10)
        settings_frame.grid(row=3, column=0, padx=10, pady=5, sticky='ew')

        # Период обновления
        ttk.Label(settings_frame, text="Интервал обновления (сек):").grid(row=0, column=0, sticky='w')
        self.period_spinbox = ttk.Spinbox(
            settings_frame,
            from_=1,
            to=60,
            width=5,
            validate="key",
            validatecommand=(self.root.register(self.validate_positive), "%P")
        )
        self.period_spinbox.set(self.update_period)
        self.period_spinbox.grid(row=0, column=1, padx=5, pady=2, sticky='e')

        # Пороговые значения
        ttk.Label(settings_frame, text="Нижний порог:").grid(row=1, column=0, sticky='w')
        self.low_threshold_spinbox = ttk.Spinbox(
            settings_frame,
            from_=0,
            to=100,
            width=5,
            state='disabled',
            validate="key",
            validatecommand=(self.root.register(self.validate_positive), "%P")
        )
        self.low_threshold_spinbox.set(self.critical_low)
        self.low_threshold_spinbox.grid(row=1, column=1, padx=5, pady=2, sticky='e')

        ttk.Label(settings_frame, text="Верхний порог:").grid(row=2, column=0, sticky='w')
        self.high_threshold_spinbox = ttk.Spinbox(
            settings_frame,
            from_=0,
            to=100,
            width=5,
            state='disabled',
            validate="key",
            validatecommand=(self.root.register(self.validate_positive), "%P")
        )
        self.high_threshold_spinbox.set(self.critical_high)
        self.high_threshold_spinbox.grid(row=2, column=1, padx=5, pady=2, sticky='e')

        # Валидация пороговых значений
        self.low_threshold_spinbox.bind('<FocusOut>', self.validate_thresholds)
        self.high_threshold_spinbox.bind('<FocusOut>', self.validate_thresholds)

    def validate_thresholds(self, event):
        try:
            low = int(self.low_threshold_spinbox.get())
            high = int(self.high_threshold_spinbox.get())
            if low >= high:
                self.high_threshold_spinbox.delete(0, 'end')
                self.high_threshold_spinbox.insert(0, str(low + 1))
        except ValueError:
            pass

    def update_pump_ui(self):
        if self.pump_status:
            self.pump_button.config(text="⏹ Остановить насос", style='Red.TButton')
            self.pump_status_label.config(text="Статус: Включен", foreground='#2ECC71')
        else:
            self.pump_button.config(text="▶ Запустить насос", style='Green.TButton')
            self.pump_status_label.config(text="Статус: Выключен", foreground='#E74C3C')

    def update_sensor_value(self):
        if self.pump_status:
            self.sensor_value = min(100, self.sensor_value + random.randint(5, 25))
        else:
            self.sensor_value = max(0, self.sensor_value - random.randint(5, 10))

        self.sensor_progress['value'] = self.sensor_value
        self.sensor_label.config(text=f"{self.sensor_value}%")

        if self.mode == "Автоматический":
            self.critical_low = int(self.low_threshold_spinbox.get())
            self.critical_high = int(self.high_threshold_spinbox.get())

            if self.sensor_value < self.critical_low:
                self.pump_status = True
            elif self.sensor_value > self.critical_high:
                self.pump_status = False
            self.update_pump_ui()

        self.mqtt_client.publish("iot/device/sensor", self.sensor_value)

        # Динамическое изменение цвета прогресс-бара
        if self.sensor_value < self.critical_low:
            self.style.configure('Horizontal.TProgressbar', background='#E74C3C')
        elif self.sensor_value > self.critical_high:
            self.style.configure('Horizontal.TProgressbar', background='#F1C40F')
        else:
            self.style.configure('Horizontal.TProgressbar', background='#3498DB')

    def sensor_update_loop(self):
        while self.running:
            time.sleep(int(self.period_spinbox.get()))
            self.update_sensor_value()

    def on_connect(self, client, userdata, flags, rc):
        print("Подключение к MQTT-брокеру завершено с кодом " + str(rc))
        client.subscribe("iot/device/response")
        client.subscribe("iot/device/mode")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        if topic == "iot/device/response" and self.mode == "Ручной":
            if payload == "on":
                self.pump_status = True
            elif payload == "off":
                self.pump_status = False
            self.update_pump_ui()

        if topic == "iot/device/mode":
            if payload == "Ручной":
                self.mode = "Ручной"
                self.mode_selector.set(self.mode)
                self.low_threshold_spinbox.config(state="disabled")
                self.high_threshold_spinbox.config(state="disabled")
            elif payload == "Автоматический":
                self.mode = "Автоматический"
                self.mode_selector.set(self.mode)
                self.low_threshold_spinbox.config(state="normal")
                self.high_threshold_spinbox.config(state="normal")

    def change_mode(self, event):
        self.mode = self.mode_selector.get()
        self.mqtt_client.publish("iot/device/mode", self.mode)

        if self.mode == "Автоматический":
            self.low_threshold_spinbox.config(state="normal")
            self.high_threshold_spinbox.config(state="normal")
        else:
            self.low_threshold_spinbox.config(state="disabled")
            self.high_threshold_spinbox.config(state="disabled")

    def toggle_pump(self):
        self.pump_status = not self.pump_status
        self.update_pump_ui()
        self.mqtt_client.publish("iot/device/pump", "on" if self.pump_status else "off")


if __name__ == "__main__":
    root = tk.Tk()
    app = IoTDeviceSimulator(root)
    root.mainloop()
