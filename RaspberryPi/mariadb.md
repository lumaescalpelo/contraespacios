# MariaDB

En este documento se describe la creación de los usuarios, bases de datos y tablas necesarias para este proyecto.

Desde una terminal entra a MariaDB.
```
sudo mysql -u root -p
```

Crea la base de datos.
```
CREATE DATABASE ambiente
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Crea un usuario con permisos de escritura para Node-Red.
```
CREATE USER 'cinema'@'localhost' IDENTIFIED BY 'barredura';

GRANT SELECT, INSERT, UPDATE
ON ambiente.* 
TO 'cinema'@'localhost';
```

Crea un usuario con permisos solo de lectura para Grafana.
```
CREATE USER 'cinema_ro'@'localhost' IDENTIFIED BY 'barredura';

GRANT SELECT
ON ambiente.* 
TO 'cinema_ro'@'localhost';
```

Aplica los permisos.
```
FLUSH PRIVILEGES;
```

Crea la base de datos.

```
USE ambiente;

CREATE TABLE registros_ambiente (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ts DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

  dispositivo VARCHAR(32) NULL,
  lugar VARCHAR(128) NULL,
  archivo_nombre VARCHAR(255) NULL,

  temperatura DECIMAL(6,2) NULL,   -- °C
  humedad     DECIMAL(6,2) NULL,   -- %
  aqi         TINYINT UNSIGNED NULL,
  tvoc        INT UNSIGNED NULL,   -- ppb
  eco2        INT UNSIGNED NULL,   -- ppm

  valido TINYINT(1) NULL DEFAULT NULL,
  notas VARCHAR(255) NULL,

  PRIMARY KEY (id),
  INDEX idx_ts (ts),
  INDEX idx_dispositivo_ts (dispositivo, ts),
  INDEX idx_lugar_ts (lugar, ts)
) ENGINE=InnoDB;
```

Aquí está la versión de una sola linea.
```
CREATE TABLE registros_ambiente (id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, ts DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3), dispositivo VARCHAR(32) NULL, lugar VARCHAR(128) NULL, archivo_nombre VARCHAR(255) NULL, temperatura DECIMAL(6,2) NULL, humedad DECIMAL(6,2) NULL, aqi TINYINT UNSIGNED NULL, tvoc INT UNSIGNED NULL, eco2 INT UNSIGNED NULL, valido TINYINT(1) NULL DEFAULT NULL, notas VARCHAR(255) NULL, PRIMARY KEY (id), INDEX idx_ts (ts), INDEX idx_dispositivo_ts (dispositivo, ts), INDEX idx_lugar_ts (lugar, ts)) ENGINE=InnoDB;
```

Verifica la existencia de la base.
```
SHOW DATABASES LIKE 'ambiente';
```

Verás algo como lo siguiente.
```
+---------------------+
| Database (ambiente) |
+---------------------+
| ambiente            |
+---------------------+
```

Ve la tabla.
```
SHOW DATABASES LIKE 'ambiente';
```

Verás algo como lo siguiente.
```
+--------------------+
| Tables_in_ambiente |
+--------------------+
| registros_ambiente |
+--------------------+
```

Ve la estructura.
```
DESCRIBE ambiente.registros_ambiente;
```

Verás algo como lo siguiente.
```
+----------------+---------------------+------+-----+----------------------+----------------+
| Field          | Type                | Null | Key | Default              | Extra          |
+----------------+---------------------+------+-----+----------------------+----------------+
| id             | bigint(20) unsigned | NO   | PRI | NULL                 | auto_increment |
| ts             | datetime(3)         | NO   | MUL | current_timestamp(3) |                |
| dispositivo    | varchar(32)         | YES  | MUL | NULL                 |                |
| lugar          | varchar(128)        | YES  | MUL | NULL                 |                |
| archivo_nombre | varchar(255)        | YES  |     | NULL                 |                |
| temperatura    | decimal(6,2)        | YES  |     | NULL                 |                |
| humedad        | decimal(6,2)        | YES  |     | NULL                 |                |
| aqi            | tinyint(3) unsigned | YES  |     | NULL                 |                |
| tvoc           | int(10) unsigned    | YES  |     | NULL                 |                |
| eco2           | int(10) unsigned    | YES  |     | NULL                 |                |
| valido         | tinyint(1)          | YES  |     | NULL                 |                |
| notas          | varchar(255)        | YES  |     | NULL                 |                |
+----------------+---------------------+------+-----+----------------------+----------------+
```