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

## Node.JS

Instalar NodeJS con los siguientes comandos

```
sudo apt update
sudo apt install -y curl

curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

Comprobar que estén instalados con los siguientes comandos

```
node -v
npm -v
```

## Node-Red

Instalar Node-Red con el siguiente comando.

```
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
```

- Dejar todas las configuraciones como predeterminadas
- Configurar seguridad con usuario `cinema` y password `barredura`
- Usar frase de encriptado `cinemabarredura`

Se puede probar el funcionamiento ejecutando el comando `node-red` y entrando a `http://127.0.0.1:1880/`

**Recomendación**: Configurar Firefox para que abra las pestañas anteriores al arrancar

Activar Node-Red al iniciar el sistema
```
sudo systemctl enable nodered.service
sudo systemctl start nodered.service
```

Comprobar estado de Node-Red
```
systemctl status nodered.service
```

Puedes consultar los logs con el siguiente comando
```
journalctl -u nodered -f
```

Comprobar que todo quedó correcto reiniciando la Raspberry Pi y visitando `http://127.0.0.1:1880/`

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

