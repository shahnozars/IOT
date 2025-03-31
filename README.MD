Перед запуском:
1. убедитесь, что установлена библиотека tkinter
  - Для установки на ubuntu `sudo apt install python3-tk`
2. Создайте виртуальное окружение и установите зависимости
```sh
mkdir venv;
python3 -m venv ./venv/ ;
source ./venv/bin/activate ;
pip install -r requirements.txt ;
```
3. Запустите симулятор
```sh
python3 main.py
```
4. Запустите mqtt (в отдельной сессии)
```sh
python3 mqttProcessor.py
```