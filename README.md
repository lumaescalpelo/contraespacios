    # Contra Espacios

    Proyecto de Amaranta Chikiframe.

    Contra Espacios es un sistema portátil que toma variables ambientales de distintos lugares y las traduce en dibujos sobre película de cine de 16 mm. El proyecto utiliza una Raspberry Pi como computadora principal, un sistema de dibujo tipo CNC, sensores ambientales, una ESP32CAM y un flujo automatizado para registrar datos, generar gráficos y controlar el movimiento de la máquina.

    El proyecto antes se llamaba `cinemabarredura`.

    ---

    ## 1. Descripción general

    Contra Espacios consiste en una máquina de dibujo sobre película cinematográfica. El sistema registra variables ambientales, captura imágenes del entorno o del estado de la máquina, procesa esa información y la convierte en instrucciones de dibujo.

    La máquina está pensada para funcionar de manera portátil, usando una Raspberry Pi como centro de control. La Raspberry Pi gestionará la lectura del sensor ambiental, la base de datos, la comunicación con la ESP32CAM, la automatización con Node-RED y el envío de instrucciones al sistema CNC.

    La computadora de desarrollo principal será una workstation con Fedora 44. Desde ahí se editará el repositorio, se preparará la documentación, se cargarán programas al Arduino y a la ESP32CAM, y se harán pruebas de generación gráfica. La Raspberry Pi se usará como computadora de ejecución dentro de la máquina.

    ---

    ## 2. Decisiones actuales del proyecto

    Estas decisiones sustituyen versiones anteriores del documento.

    1. La base de datos principal será **MariaDB**.
    2. El sensor ENS160 + AHT2X se conectará directo a la Raspberry Pi por I2C.
    3. La ESP32CAM se usará para captura de imagen por WiFi.
    4. Node-RED será el orquestador del sistema.
    5. Se incluyen pruebas de cada módulo.
    6. Los límites de dibujo se definirán a partir de la película colocada en el dispositivo.
    7. Una prueba clave será dibujar un círculo dentro del área útil de película.
    8. El flujo completo se ejecutará mediante cuatro botones físicos presionados en secuencia.
    9. La pantalla OLED indicará el estado actual del sistema y qué paso falta realizar.

    ---

    ## 3. Objetivo técnico del proyecto

    Construir un flujo funcional donde:

    1. La Raspberry Pi arranque en modo estable.
    2. La Raspberry Pi pueda usarse de forma remota mediante RealVNC.
    3. Node-RED controle el flujo general del sistema.
    4. El sensor ENS160 + AHT2X registre variables ambientales conectado directamente a la Raspberry Pi.
    5. Los datos ambientales se almacenen en MariaDB.
    6. Grafana permita visualizar los datos registrados.
    7. La ESP32CAM se conecte por WiFi y capture imágenes.
    8. La Raspberry Pi guarde las fotografías de cada prueba.
    9. La Raspberry Pi registre en base de datos las pruebas realizadas.
    10. El sistema genere un dibujo básico a partir de la foto y los datos ambientales.
    11. El dibujo se guarde como archivo SVG.
    12. El SVG se convierta en G-code.
    13. El Arduino con CNC Shield y GRBL controle el sistema de dibujo.
    14. El sistema CNC dibuje sobre película de 16 mm.
    15. La OLED muestre el estado de la secuencia.
    16. Los botones físicos permitan avanzar por el flujo en etapas.
    17. Todo el proceso quede documentado y versionado en GitHub.

    ---

    ## 4. Hardware requerido

    ### 4.1 Computadora principal de ejecución

    - Raspberry Pi 3B+.
    - Memoria micro SD de 32 GB o más.
    - Power bank o fuente de alimentación estable.
    - Cable USB para conectar Arduino / controlador CNC.
    - Red WiFi local o punto de acceso propio.
    - Acceso remoto mediante RealVNC.

    ### 4.2 Computadora de desarrollo

    - Workstation con Fedora 44.
    - Visual Studio Code.
    - GitHub Desktop.
    - Arduino IDE.
    - RealVNC Viewer.
    - Navegador web.
    - Python.
    - Conexión a GitHub.

    ### 4.3 Sistema de movimiento

    - Sistema de dibujo tipo CNC.
    - Motores a pasos.
    - CNC Shield.
    - Drivers para motores a pasos.
    - Sensores de límite.
    - Estructura mecánica impresa en 3D.
    - Herramienta de dibujo o mecanismo de contacto con la película.

    ### 4.4 Sensores y periféricos

    - Sensor ENS160 + AHT2X.
    - ESP32CAM.
    - Pantalla OLED.
    - 4 botones físicos.
    - Cables Dupont.
    - Placa universal para botonera.
    - Resistencias y conectores necesarios.
    - Imanes pequeños.
    - Sensores Hall digitales A3144 para finales de carrera.

    ### 4.5 Alimentación

    - Power bank para la Raspberry Pi.
    - Fuente o conversor adecuado para motores.
    - Reguladores o módulos step-up / step-down si son necesarios.
    - Cables cortos y firmes para reducir falsos contactos.
    - Alimentación separada o suficientemente estable para que los motores no reinicien la Raspberry Pi.

    ---

    ## 5. Software requerido

    ### 5.1 En la computadora de desarrollo

    La computadora de desarrollo principal fue una workstation con Fedora 44.

    Se usó para:

    - Editar documentación.
    - Escribir scripts.
    - Administrar el repositorio de GitHub.
    - Preparar archivos de configuración.
    - Hacer pruebas de generación de gráficos.
    - Cargar firmware al Arduino.
    - Cargar programa a la ESP32CAM.
    - Hacer commits y subir cambios.

    Software requerido:

    - GitHub Desktop.
    - Visual Studio Code.
    - Python.
    - Arduino IDE.
    - RealVNC Viewer.
    - Navegador web.
    - Herramientas de documentación.

    ### 5.2 En la Raspberry Pi

    La Raspberry Pi será la computadora de ejecución del proyecto.

    Software requerido:

    - Raspberry Pi OS Trixie.
    - Node.js.
    - Node-RED.
    - MariaDB.
    - Grafana.
    - Python.
    - Git.
    - RealVNC.
    - Herramientas I2C.
    - GRBL sender o software para controlar GRBL.
    - bCNC.
    - vpype.
    - GcodeTools o herramienta equivalente de conversión cuando sea útil.

    No se usará Mosquitto en la versión actual del flujo.

    ### 5.3 En el Arduino / CNC Shield

    El Arduino conectado al CNC Shield ejecutará GRBL.

    Uso previsto:

    - Recibir G-code por USB desde la Raspberry Pi.
    - Controlar los drivers del CNC Shield.
    - Mover los motores del sistema de dibujo.
    - Leer sensores de límite.
    - Ejecutar homing cuando los límites estén funcionando.
    - Reportar estado de máquina a la Raspberry Pi.

    ### 5.4 En la ESP32CAM

    La ESP32CAM tendrá el programa de cámara modificado para cumplir lo siguiente:

    - Conectarse por WiFi.
    - Tener nombre de host para que pueda ser encontrada por la Raspberry Pi aunque tenga una IP diferente.
    - Tomar fotografías.
    - Servir la imagen por HTTP.
    - Confirmar estado de conexión.
    - Reiniciar de forma segura si pierde conexión.

    Endpoint sugerido para captura:

    ```text
    /capture
    ```

    ---

    ## 6. Estado actual del repositorio

    El repositorio ya contiene las siguientes áreas de trabajo:

    ```text
    /README.md
    /ESP32CAM/
    /MariaDB/
    /Node-Red/
    /RaspberryPi/
    /CNC/
    /Sensores/
    ```

    ### 6.1 README general

    Este archivo funciona como mapa del proyecto. Debe describir la lógica general, el orden de trabajo y el estado actual, sin sustituir los documentos específicos de cada módulo.

    ### 6.2 RaspberryPi

    La carpeta `RaspberryPi` contiene instrucciones de instalación y configuración de la Raspberry Pi.

    Actualmente también contiene `mariadb.md`, pero esta información debe moverse a una carpeta dedicada para base de datos.

    Reorganización sugerida:

    ```text
    /RaspberryPi/README.md  
    /BaseDeDatos/README.md
    ```

    `RaspberryPi/README.md` debe conservar la instalación general del sistema operativo, VNC, Node.js, Node-RED, Grafana y herramientas necesarias.

    `BaseDeDatos/README.md` debe contener la instalación y configuración de MariaDB, usuarios, permisos, tablas y consultas.

    ### 6.3 Node-Red

    La carpeta `Node-Red` contiene:

    ```text
    /Node-Red/README.md
    /Node-Red/flows.json
    ```

    Ya se hicieron ejercicios de prueba en Node-RED. La documentación general debe partir de ese avance y describir lo que sigue, no repetir como si el sistema estuviera en cero. 

    El flujo actual sirve como base de experimentación. La lógica futura será crear flujos pequeños, verificables y separados para cada parte del sistema.

    ### 6.4 ESP32CAM

    La carpeta `ESP32CAM` contiene programas relacionados con la cámara.    

    ### 6.5 CNC

    La carpeta `CNC` quedará dedicada al firmware, pruebas de movimiento, límites, coordenadas de trabajo, G-code y pruebas de dibujo.

    ### 6.6 Sensores

    La carpeta `Sensores` debe contener la documentación y programas de lectura del ENS160 + AHT2X conectado directo a la Raspberry Pi.

    ---

    ## 7. Estrategia de desarrollo

    El proyecto no se desarrollará como un solo flujo gigante. Se trabajará por módulos.

    La lógica será:

    ```text
    1. Probar una parte por sí misma.
    2. Confirmar que funciona.
    3. Documentar la prueba.
    4. Integrarla a Node-RED.
    5. Confirmar que funciona desde Node-RED.
    6. Guardar el flujo.
    7. Pasar al siguiente módulo.
    ```

    ---

    ## 8. Flujo físico de operación con botones

    El sistema tendrá cuatro botones físicos. Se presionarán en secuencia.

    ### Botón 1: capturar foto

    Acción:

    1. Solicitar imagen a la ESP32CAM.
    2. Guardar la imagen en la Raspberry Pi.
    3. Registrar la captura en MariaDB.
    4. Actualizar estado en OLED.
    5. Confirmar en Node-RED que la captura fue correcta.

    Estado esperado en OLED:

    ```text
    1 FOTO
    OK / ERROR
    ```

    ### Botón 2: capturar ambiente

    Acción:

    1. Leer el sensor ENS160 + AHT2X desde la Raspberry Pi.
    2. Guardar temperatura, humedad, AQI, TVOC y eCO2 en MariaDB.
    3. Asociar la lectura a la prueba actual.
    4. Actualizar estado en OLED.
    5. Confirmar en Node-RED que la lectura fue correcta.

    Estado esperado en OLED:

    ```text
    2 AMBIENTE
    OK / ERROR
    ```

    ### Botón 3: generar dibujo y G-code

    Acción:

    1. Tomar la foto guardada.
    2. Tomar la lectura ambiental asociada.
    3. Generar un dibujo básico.
    4. Guardar el dibujo como SVG.
    5. Convertir el SVG a G-code.
    6. Guardar el G-code.
    7. Registrar los archivos generados en MariaDB.
    8. Actualizar estado en OLED.

    Estado esperado en OLED:

    ```text
    3 GENERAR
    SVG / GCODE OK
    ```

    ### Botón 4: ejecutar dibujo

    Acción:

    1. Confirmar que existe foto.
    2. Confirmar que existe lectura ambiental.
    3. Confirmar que existe SVG.
    4. Confirmar que existe G-code.
    5. Confirmar que la máquina está lista.
    6. Enviar G-code a GRBL.
    7. Dibujar sobre la película.
    8. Registrar resultado en MariaDB.
    9. Actualizar estado en OLED.

    Estado esperado en OLED:

    ```text
    4 DIBUJAR
    RUN / DONE / ERROR
    ```

    ---

    ## 9. Pantalla OLED

    La pantalla OLED debe funcionar como guía de estado.

    Debe indicar:

    - En qué paso está el sistema.
    - Qué paso falta.
    - Si la última acción fue correcta.
    - Si hubo error.
    - Si falta capturar foto.
    - Si falta capturar ambiente.
    - Si falta generar dibujo.
    - Si falta ejecutar G-code.

    Estados sugeridos:

    ```text
    INICIO
    FALTA FOTO
    FOTO OK
    FALTA AMBIENTE
    AMBIENTE OK
    FALTA SVG
    SVG OK
    FALTA GCODE
    GCODE OK
    LISTO PARA DIBUJAR
    DIBUJANDO
    TERMINADO
    ERROR
    ```

    La OLED no debe contener la lógica principal. Solo debe mostrar el estado del sistema. La lógica principal vivirá en Node-RED y scripts ejecutados por la Raspberry Pi.

    ---

    ## 10. Base de datos

    La base de datos principal será MariaDB.

    ### 10.1 Datos ambientales

    La tabla existente de ambiente puede registrar:

    - Temperatura.
    - Humedad.
    - AQI.
    - TVOC.
    - eCO2.
    - Lugar.
    - Notas.
    - Archivo asociado.
    - Fecha y hora.

    ### 10.2 Datos que deben agregarse

    Para el flujo completo se necesitarán más tablas o una ampliación del esquema.

    Datos a registrar:

    - Sesión o prueba.
    - Fotografía capturada.
    - Lectura ambiental usada.
    - SVG generado.
    - G-code generado.
    - Estado de ejecución.
    - Resultado.
    - Errores.
    - Notas manuales.

    Tablas sugeridas:

    ```text
    registros_ambiente
    pruebas
    capturas
    dibujos
    eventos_maquina
    ```

    ### 10.3 Reorganización de documentación

    Mover:

    ```text
    /RaspberryPi/mariadb.md
    ```

    a:

    ```text
    /BaseDeDatos/README.md
    ```

    La carpeta de Raspberry Pi debe quedar para sistema operativo y servicios generales.

    La carpeta de base de datos debe concentrar la estructura y consultas.

    ---

    ## 11. Sensor ENS160 + AHT2X

    El sensor ambiental se conectará directamente a la Raspberry Pi por I2C.

    Ya no se usará el flujo anterior donde un ESP32 leía el sensor y enviaba datos por MQTT.

    ### 11.1 Próximos pasos

    1. Conectar físicamente el sensor a la Raspberry Pi.
    2. Confirmar dirección I2C.
    3. Hacer una lectura simple desde terminal o Python.
    4. Guardar una lectura en MariaDB.
    5. Hacer un flujo Node-RED que ejecute o reciba esa lectura.
    6. Confirmar que Node-RED puede guardar la lectura en MariaDB.
    7. Confirmar que Grafana puede leer esos datos.
    8. Documentar el procedimiento en `Sensores/README.md`.

    ---

    ## 12. ESP32CAM

    La ESP32CAM se usará para capturar imágenes por WiFi.

    ### 12.1 Próximos pasos

    1. Revisar el programa `CameraWebServer`.
    2. Ajustar WiFi y nombre de host.
    3. Cargar el programa desde Arduino IDE.
    4. Confirmar que la cámara responde desde navegador.
    5. Confirmar que la Raspberry Pi puede descargar una imagen.
    6. Guardar la imagen con nombre único.
    7. Registrar la captura en MariaDB.
    8. Crear un flujo de Node-RED para capturar imagen.
    9. Documentar el procedimiento en `ESP32CAM/README.md`.

    ---

    ## 13. Node-RED

    Node-RED será el tablero de integración del proyecto.

    ### 13.1 Lo que ya existe

    Ya se hicieron ejercicios de prueba. El repositorio contiene un `flows.json` inicial y un README de Node-RED con notas sobre usuario, contraseña, frase de encriptación y nodos externos.

    ### 13.2 Lógica de trabajo en Node-RED

    Cada función importante debe existir como flujo pequeño antes de integrarse al flujo completo.

    Flujos sugeridos:

    1. Prueba de dashboard.
    2. Prueba de conexión a MariaDB.
    3. Prueba de captura de imagen.
    4. Prueba de lectura ambiental.
    5. Prueba de guardado de lectura ambiental.
    6. Prueba de generación de SVG.
    7. Prueba de generación de G-code.
    8. Prueba de envío a GRBL.
    9. Prueba de botones físicos.
    10. Prueba de OLED.
    11. Flujo completo secuencial.

    ### 13.3 Flujo completo previsto

    ```text
    Botón 1
    ↓
    Capturar foto
    ↓
    Guardar foto
    ↓
    Registrar captura
    ↓
    OLED: FOTO OK

    Botón 2
    ↓
    Leer ambiente
    ↓
    Guardar lectura
    ↓
    OLED: AMBIENTE OK

    Botón 3
    ↓
    Generar dibujo básico
    ↓
    Guardar SVG
    ↓
    Generar G-code
    ↓
    Guardar G-code
    ↓
    OLED: DIBUJO OK

    Botón 4
    ↓
    Ejecutar G-code
    ↓
    Registrar resultado
    ↓
    OLED: TERMINADO
    ```

    ---

    ## 14. CNC y área de dibujo

    El sistema CNC debe trabajar dentro del área útil real de la película colocada en el dispositivo.

    Los límites de dibujo no deben inventarse desde el software. Deben medirse a partir de la película, la ventana mecánica y el recorrido seguro del sistema.

    ### 14.1 Coordenadas de trabajo

    Se deberán definir:

    - Origen de trabajo.
    - Ancho útil.
    - Alto útil.
    - Margen de seguridad.
    - Dirección X.
    - Dirección Y o Z temporal.
    - Velocidad segura.
    - Escala de conversión entre SVG y máquina.

    ### 14.2 Prueba de círculo

    Una prueba importante será dibujar un círculo dentro del área útil.

    Objetivos de la prueba:

    1. Confirmar escala.
    2. Confirmar proporción entre ejes.
    3. Confirmar que el dibujo cabe en película.
    4. Confirmar que el círculo no se vuelve elipse por mala calibración.
    5. Confirmar que el origen es repetible.
    6. Confirmar que no se sale del área segura.

    Resultado esperado:

    ```text
    Un círculo centrado dentro del área útil de dibujo.
    ```

    ### 14.3 Próximos pasos CNC

    1. Cargar GRBL en Arduino.
    2. Confirmar comunicación desde Raspberry Pi.
    3. Probar bCNC.
    4. Probar movimientos cortos.
    5. Conectar límites Hall A3144.
    6. Configurar homing.
    7. Medir área útil sobre película.
    8. Generar G-code de círculo.
    9. Ejecutar círculo sin herramienta.
    10. Ejecutar círculo sobre papel.
    11. Ejecutar círculo sobre película de prueba.

    ---

    ## 15. Generación de dibujo

    La generación de dibujo debe partir de una prueba registrada.

    Cada prueba debe tener:

    1. Foto.
    2. Lectura ambiental.
    3. Registro en base de datos.
    4. SVG generado.
    5. G-code generado.
    6. Resultado de ejecución.

    ### 15.1 Dibujo básico inicial

    La primera versión no necesita ser compleja.

    Puede ser:

    - Círculo.
    - Línea ondulada.
    - Contorno simple.
    - Blob básico.
    - Patrón modulado por temperatura, humedad, TVOC, eCO2 o AQI.

    La prioridad es que el flujo completo funcione.

    ### 15.2 Flujo de archivos

    ```text
    foto capturada
    ↓
    datos ambientales
    ↓
    dibujo básico
    ↓
    archivo SVG
    ↓
    archivo G-code
    ↓
    dibujo sobre película
    ```

    ### 15.3 Guardado de archivos

    Cada prueba debe guardar:

    ```text
    /fotos/
    /svg/
    /gcode/
    /resultados/
    ```

    La estructura definitiva se definirá después, pero el README general debe dejar clara la obligación de guardar los archivos generados. Sin eso, luego nadie sabe qué archivo produjo qué dibujo, y el archivo `final_final_ahora_si.gcode` se convierte en patrimonio de la desesperación.

    ---

    ## 16. Etapas de trabajo actualizadas

    ### Etapa 1: Raspberry Pi

    - [ ] Instalar Raspberry Pi OS.
    - [ ] Configurar usuario.
    - [ ] Configurar red.
    - [ ] Activar SSH.
    - [ ] Activar RealVNC.
    - [ ] Activar I2C.
    - [ ] Confirmar acceso remoto.
    - [ ] Clonar repositorio en Raspberry Pi.

    ### Etapa 2: clonar repositorio en Raspberry Pi

    - [ ] Instalar Git si hace falta.
    - [ ] Crear carpeta de trabajo.
    - [ ] Clonar repositorio.
    - [ ] Confirmar que aparecen las carpetas del proyecto.
    - [ ] Probar `git pull`.
    - [ ] Confirmar que la Raspberry Pi ejecutará los archivos desde el repositorio local.

    ### Etapa 3: Node-RED

    - [x] Instalar Node-RED.
    - [x] Hacer ejercicios de prueba.
    - [x] Crear o importar `flows.json`.
    - [ ] Revisar flujo actual.
    - [ ] Eliminar dependencias de MQTT del flujo futuro.
    - [ ] Mantener o archivar pruebas anteriores.
    - [ ] Crear flujo de prueba para captura de foto.
    - [ ] Crear flujo de prueba para lectura ambiental directa desde Raspberry Pi.
    - [ ] Crear flujo de prueba para MariaDB.
    - [ ] Crear flujo de prueba para botones.
    - [ ] Crear flujo de prueba para OLED.

    ### Etapa 4: MariaDB

    - [ ] Mover documentación de MariaDB a carpeta dedicada.
    - [ ] Confirmar base de datos `ambiente`.
    - [ ] Confirmar usuario de escritura para Node-RED.
    - [ ] Confirmar usuario de lectura para Grafana.
    - [ ] Confirmar tabla `registros_ambiente`.
    - [ ] Diseñar tablas para pruebas, capturas, dibujos y eventos.
    - [ ] Conectar Node-RED a MariaDB.
    - [ ] Conectar Grafana a MariaDB.

    ### Etapa 5: sensor ENS160 + AHT2X

    - [ ] Mover o archivar programas ESP32 antiguos de lectura ambiental.
    - [ ] Crear documentación de sensor conectado directo a Raspberry Pi.
    - [ ] Conectar sensor por I2C.
    - [ ] Confirmar dirección I2C.
    - [ ] Leer datos desde Raspberry Pi.
    - [ ] Guardar datos en MariaDB.
    - [ ] Crear flujo Node-RED de lectura ambiental.

    ### Etapa 6: ESP32CAM

    - [ ] Ajustar documentación de ESP32CAM para enfocarla en cámara.
    - [ ] Revisar `CameraWebServer`.
    - [ ] Configurar WiFi.
    - [ ] Configurar hostname.
    - [ ] Probar endpoint `/capture`.
    - [ ] Guardar foto en Raspberry Pi.
    - [ ] Registrar foto en MariaDB.
    - [ ] Crear flujo Node-RED de captura de foto.

    ### Etapa 7: CNC

    - [ ] Cargar GRBL en Arduino.
    - [ ] Probar comunicación desde Raspberry Pi.
    - [ ] Instalar y probar bCNC.
    - [ ] Probar movimientos cortos.
    - [ ] Conectar límites A3144.
    - [ ] Configurar homing.
    - [ ] Medir límites reales de dibujo según película.
    - [ ] Definir coordenadas de trabajo.
    - [ ] Dibujar círculo de prueba.
    - [ ] Documentar valores de calibración.

    ### Etapa 8: generación SVG y G-code

    - [ ] Generar SVG básico desde datos de prueba.
    - [ ] Guardar SVG.
    - [ ] Convertir SVG a G-code.
    - [ ] Guardar G-code.
    - [ ] Registrar ambos archivos en MariaDB.
    - [ ] Crear flujo Node-RED para generación de dibujo.
    - [ ] Crear flujo Node-RED para generación de G-code.

    ### Etapa 9: botones y OLED

    - [ ] Conectar 4 botones.
    - [ ] Probar cada botón.
    - [ ] Asignar función a cada botón.
    - [ ] Conectar OLED.
    - [ ] Mostrar estado inicial.
    - [ ] Mostrar estado de cada paso.
    - [ ] Mostrar errores.
    - [ ] Integrar botones y OLED con Node-RED o scripts de Raspberry Pi.

    ### Etapa 10: flujo completo

    - [ ] Botón 1 captura foto.
    - [ ] Botón 2 captura ambiente.
    - [ ] Botón 3 genera SVG y G-code.
    - [ ] Botón 4 ejecuta dibujo.
    - [ ] OLED muestra avance.
    - [ ] MariaDB registra la prueba completa.
    - [ ] Grafana visualiza datos ambientales.
    - [ ] Se guarda foto, SVG y G-code.
    - [ ] La máquina dibuja dentro de los límites de película.

    ---

    ## 17. Documentación pendiente por módulo

    Se crearán READMEs específicos para cada parte.

    Pendientes:

    ```text
    /RaspberryPi/README.md
    /BaseDeDatos/README.md
    /Node-Red/README.md
    /ESP32CAM/README.md
    /Sensores/README.md
    /CNC/README.md
    /OLED_Botones/README.md
    /Grafana/README.md
    ```

    Cada README específico debe contener instrucciones detalladas, comandos, conexiones, errores encontrados y solución.

    El README general solo debe marcar el mapa y el estado de avance.

    ---

    ## 18. Estado actual

    ### Ya existe

    - [x] README general inicial.
    - [x] Carpeta `RaspberryPi`.
    - [x] Documentación inicial de Raspberry Pi.
    - [x] Documento `mariadb.md` dentro de `RaspberryPi`.
    - [x] Carpeta `Node-Red`.
    - [x] Archivo `flows.json` inicial.
    - [x] README inicial de Node-RED.
    - [x] Carpeta `ESP32CAM`.
    - [x] Programas previos de lectura ENS160 + AHT21 desde ESP32.
    - [x] Programa base `CameraWebServer`.
    - [x] Carpetas `CNC` y `Sensores`.

    ### Hay que corregir

    - [ ] Quitar Mosquitto del README general.
    - [ ] Quitar MQTT como ruta principal.
    - [ ] Mover documentación de MariaDB a carpeta dedicada.
    - [ ] Separar ESP32CAM de lectura ambiental.
    - [ ] Replantear sensor ENS160 + AHT2X como sensor directo a Raspberry Pi.
    - [ ] Actualizar Node-RED para reflejar pruebas por módulo.
    - [ ] Definir área de dibujo real según película.
    - [ ] Agregar lógica de cuatro botones.
    - [ ] Agregar lógica de OLED como pantalla de estado.

    ### Siguiente paso recomendado

    El siguiente paso es ordenar documentación antes de escribir más código:

    1. Mover `RaspberryPi/mariadb.md` a `BaseDeDatos/README.md`.
    2. Ajustar `ESP32CAM/README.md` para que sea solo de cámara.
    3. Crear `Sensores/README.md` para ENS160 + AHT2X directo a Raspberry Pi.
    4. Revisar `Node-Red/README.md` para explicar la lógica de pruebas por módulo.
    5. Después continuar con el sensor ambiental directo a Raspberry Pi.