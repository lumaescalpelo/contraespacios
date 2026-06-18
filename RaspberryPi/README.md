# Raspberry Pi

En este documento encontrarás las configuraciones necesarias para hacer funcionar este proyecto

## Sistema

- Configurar como nombre de usuaro `pi` y como contraseña `raspberry`
- Asegurarse de que esté activado SSH y VNC con `sudo raspi-config` o con Control centre
- Se recomienda usar una Raspberry Pi 4B+
- Se recomienda usar una resolución de pantalla de 1280x720
- Configurar FireFox como navegador predeterminado
- No desinstalar Chrome

## Software

Se requiere contar con lo siguiente:

- Node.JS
- Node-Red
- MariaDB Server
- Grafana
- Mosquitto



## MariaDB

Instalar María DB Server con los siguientes comandos.

```
sudo apt update
sudo apt install -y mariadb-server
```


Comprobar que el servicio funciona.
```
sudo systemctl status mariadb
```


Comprobar entrando al CLI de MariaDB
```
sudo mysql -u root -p
```

Debe verse algo como `MariaDB [(none)]>`

Salir de MariaDB CLI.
```
exit;
```

## Grafana

Instala Grafana con los siguientes comandos.

```
sudo apt update
sudo apt install -y apt-transport-https software-properties-common wget
```

Agrega la clave GPG.
```
sudo mkdir -p /etc/apt/keyrings
wget -q -O - https://apt.grafana.com/gpg.key | sudo tee /etc/apt/keyrings/grafana.key > /dev/null
```

Agrega el repositorio-
```
echo "deb [signed-by=/etc/apt/keyrings/grafana.key] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
```

Actualiza.
```
sudo apt update
```

Instala Grafana
```
sudo apt install -y grafana
```

Habilita el inicio automático de Grafana
```
sudo systemctl daemon-reload
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

Verifica que esté funcionando.
```
systemctl status grafana-server
```

Abre Grafana desde un navegador en la Raspberry Pi en `127.0.0.1:3000` e inicia sesión con el usuario `admin` y la contraseña `admin`. Te pedirá que cambies la contraseña, escribe `barredura`.

## Mosquitto

Instala Grafana con los siguientes comandos.
```
sudo apt update
sudo apt upgrade -y
```

Instala Mosquitto.
```
sudo apt install mosquitto mosquitto-clients -y
```

Habilita el inicio de mosquitt con el sistema.
```
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

Comprueba que este funcionando.
```
sudo systemctl status mosquitto
```

Realiza una prueba. 

Ejecuta en una terminal el siguiente comando para suscribirte a un tema `mosquitto_sub -h localhost -t prueba`y en otra terminal ejecuta el siguiente comando para enviar un mensane `mosquitto_pub -h localhost -t prueba -m "hola mosquitto"`. Debrás recibir el mensaje en la primer terminal.

Edita el archivo de configuraciones para recibir conexiones externas.
```
sudo nano /etc/mosquitto/conf.d/default.conf
```

Coloca el siguiente contenido.
```
allow_anonymous false
password_file /etc/mosquitto/passwd
listener 1883 0.0.0.0
```

Reinicia Mosquitto.
```
sudo systemctl restart mosquitto
```

Ahora puedes recibir mensajes externos.