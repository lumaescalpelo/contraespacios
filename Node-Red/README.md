# Node-RED en Raspberry Pi - instalación corregida

Este documento corrige la instalación de Node-RED para Raspberry Pi cuando aparece el error:

```text
Unsupported version of Node.js: v20.20.2
Node-RED requires Node.js v22.9 or later
```

El problema es que Node-RED quedó instalado en una versión que requiere Node.js más nuevo, pero el sistema todavía tiene Node.js 20.

---

## 1. Diagnóstico

Comprobar la versión actual de Node.js:

```bash
node -v
```

Comprobar la versión de npm:

```bash
npm -v
```

Comprobar el estado del servicio:

```bash
systemctl status nodered.service
```

Consultar logs:

```bash
journalctl -u nodered -f
```

Si aparece:

```text
Unsupported version of Node.js: v20.20.2
Node-RED requires Node.js v22.9 or later
```

hay que actualizar Node.js.

---

## 2. Detener Node-RED antes de actualizar

```bash
sudo systemctl stop nodered.service
```

---

## 3. Actualizar Node.js a versión 22

Instalar herramientas necesarias:

```bash
sudo apt update
sudo apt install -y curl ca-certificates gnupg
```

Agregar el repositorio de NodeSource para Node.js 22:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
```

Instalar Node.js:

```bash
sudo apt install -y nodejs
```

Comprobar versión:

```bash
node -v
npm -v
```

La versión de Node.js debe ser 22 o superior:

```text
v22.x.x
```

---

## 4. Reinstalar o actualizar Node-RED con el instalador oficial

Usar el instalador actual recomendado para Debian/Raspberry Pi:

```bash
bash <(curl -sL https://github.com/node-red/linux-installers/releases/latest/download/install-update-nodered-deb)
```

Durante la instalación:

- Dejar las opciones predeterminadas si no hay una razón específica para cambiarlas.
- Configurar seguridad si el instalador lo pregunta.
- Usuario sugerido: `cinema`
- Contraseña sugerida: `barredura`
- Frase de encriptación: `cinemabarredura`

---

## 5. Reconstruir dependencias de Node-RED

Después de cambiar Node.js, reconstruir dependencias dentro del directorio de usuario de Node-RED:

```bash
cd ~/.node-red
npm rebuild
```

Si tienes nodos externos instalados, esto ayuda a reconstruir componentes que dependen de la versión de Node.js.

---

## 6. Instalar nodos externos necesarios

Desde la interfaz web de Node-RED:

```text
Menu -> Manage Palette -> Install
```

Instalar:

```text
@flowfuse/node-red-dashboard
node-red-node-mysql
```

También se pueden instalar por terminal:

```bash
cd ~/.node-red
npm install @flowfuse/node-red-dashboard node-red-node-mysql
```

---

## 7. Activar y arrancar el servicio

```bash
sudo systemctl enable nodered.service
sudo systemctl restart nodered.service
```

Comprobar estado:

```bash
systemctl status nodered.service
```

Ver logs en vivo:

```bash
journalctl -u nodered -f
```

También se puede usar el comando de Node-RED:

```bash
node-red-log
```

---

## 8. Abrir Node-RED

Desde la Raspberry Pi:

```text
http://127.0.0.1:1880/
```

También puede usarse:

```text
http://localhost:1880/
```

Desde otra computadora en la misma red:

```text
http://<IP_DE_LA_RASPBERRY>:1880/
```

Para ver la IP de la Raspberry Pi:

```bash
hostname -I
```

---

## 9. Importar flows.json

En Node-RED:

```text
Menu -> Import
```

Importar el archivo:

```text
flows.json
```

Después revisar:

- nodos MySQL,
- usuario,
- contraseña,
- base de datos,
- host,
- puerto.

Si los nodos MySQL muestran error, revisar credenciales.

---

## 10. Configuración usada para este proyecto

Durante la instalación o configuración de seguridad:

| Parámetro | Valor |
|---|---|
| Usuario | `cinema` |
| Contraseña | `barredura` |
| Frase de encriptación | `cinemabarredura` |

---

## 11. Comandos de administración

### Iniciar Node-RED

```bash
node-red-start
```

o:

```bash
sudo systemctl start nodered.service
```

### Detener Node-RED

```bash
node-red-stop
```

o:

```bash
sudo systemctl stop nodered.service
```

### Reiniciar Node-RED

```bash
node-red-restart
```

o:

```bash
sudo systemctl restart nodered.service
```

### Ver logs

```bash
node-red-log
```

o:

```bash
journalctl -u nodered -f
```

### Activar arranque automático

```bash
sudo systemctl enable nodered.service
```

### Desactivar arranque automático

```bash
sudo systemctl disable nodered.service
```

---

## 12. Comando completo de reparación

Este bloque actualiza Node.js a 22, reinstala Node-RED y reinicia el servicio.

```bash
sudo systemctl stop nodered.service

sudo apt update
sudo apt install -y curl ca-certificates gnupg

curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

node -v
npm -v

bash <(curl -sL https://github.com/node-red/linux-installers/releases/latest/download/install-update-nodered-deb)

cd ~/.node-red
npm rebuild
npm install @flowfuse/node-red-dashboard node-red-node-mysql

sudo systemctl enable nodered.service
sudo systemctl restart nodered.service

systemctl status nodered.service
```

---

## 13. Verificación final

Comprobar Node.js:

```bash
node -v
```

Debe mostrar:

```text
v22.x.x
```

Comprobar Node-RED:

```bash
node-red --version
```

Comprobar servicio:

```bash
systemctl status nodered.service
```

Abrir en navegador:

```text
http://127.0.0.1:1880/
```

---

## 14. Si sigue fallando

Ver logs:

```bash
journalctl -u nodered -n 100 --no-pager
```

Ver qué ejecutable de Node.js está usando:

```bash
which node
node -v
```

Ver qué ejecutable de Node-RED está usando:

```bash
which node-red
node-red --version
```

Revisar instalación global de npm:

```bash
npm list -g --depth 0
```

Reiniciar servicio:

```bash
sudo systemctl restart nodered.service
```

Ver logs otra vez:

```bash
journalctl -u nodered -f
```

---

## 15. Nota sobre Node.js 24

Node-RED actualmente recomienda Node.js 24, pero en Raspberry Pi conviene usar Node.js 22 LTS para este proyecto porque es una base estable y compatible. Si más adelante se migra todo el sistema y los nodos externos funcionan bien, puede evaluarse Node.js 24.

---

## 16. Notas del proyecto

Nodos externos requeridos:

```text
@flowfuse/node-red-dashboard
node-red-node-mysql
```

Archivo a importar:

```text
flows.json
```

Datos usados en la configuración:

```text
Usuario: cinema
Contraseña: barredura
Frase de encriptación: cinemabarredura
```
