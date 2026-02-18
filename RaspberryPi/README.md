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


