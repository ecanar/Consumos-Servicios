# Cómo encontrar y recuperar la BBDD anterior

## Objetivo

Encontrar la base de datos usada por el proyecto anterior `cnel-dashboard` y, si existe, exportarla para traerla a esta PC.

## 1. Revisar el archivo `.env` del proyecto anterior

En la otra PC, buscar el proyecto anterior y revisar:

```text
backend/.env
```

Ahí puede existir una variable como:

```text
DATABASE_URL=postgresql://...
```

Esa variable indica dónde está la base de datos.

Importante: no compartir públicamente el valor completo si contiene usuario, contraseña o URL privada.

## 2. Buscar la carpeta del proyecto anterior

En Linux:

```bash
find ~/ -type d -name "cnel-dashboard" 2>/dev/null
```

Si aparece, entrar al proyecto y revisar:

```text
backend/.env
backend/database.py
```

El proyecto anterior usaba por defecto:

```text
postgresql://postgres:postgres@localhost:5432/cnel_db
```

Por eso la base podría llamarse:

```text
cnel_db
```

## 3. Ver si existe PostgreSQL local

En la otra PC ejecutar:

```bash
psql -U postgres -l
```

Buscar una base llamada:

```text
cnel_db
```

Si existe, probablemente es la base anterior.

## 4. Exportar la base de datos PostgreSQL

Si la base se llama `cnel_db`, exportarla con:

```bash
pg_dump -U postgres -d cnel_db > cnel_db_backup.sql
```

Eso genera un archivo:

```text
cnel_db_backup.sql
```

Luego copiar ese archivo a esta PC por USB, Google Drive, red local u otro medio.

## 5. Si PostgreSQL pide contraseña

Probar con la contraseña que se usó al instalar PostgreSQL.

Si no se recuerda, revisar el archivo `.env` del proyecto anterior porque puede contener el usuario y clave usados por la app.

## 6. Revisar si se usó Docker

Si la base estaba en Docker, ejecutar:

```bash
docker ps -a
```

Buscar contenedores relacionados con:

```text
postgres
cnel
dashboard
```

Si hay un contenedor PostgreSQL, se puede exportar desde Docker con un comando específico según el nombre del contenedor.

## 7. Buscar respaldos existentes

En Linux:

```bash
find ~/ -type f \( -name "*.sql" -o -name "*.dump" -o -name "*.backup" -o -name "*.tar" \) 2>/dev/null
```

Buscar archivos con nombres parecidos a:

```text
cnel_db_backup.sql
backup.sql
postgres.dump
cnel.dump
```

## 8. ¿Sirve conectarnos a la otra PC?

Sí, serviría, pero no es obligatorio.

Opciones de conexión posibles:

```text
SSH
Samba / carpeta compartida
AnyDesk / RustDesk
Tailscale
```

Pero para este caso, lo más simple y seguro es:

```text
1. Exportar la BBDD en la otra PC
2. Copiar el archivo .sql
3. Traerlo a esta PC
```

## 9. Recomendación final

Primero intentar:

```bash
psql -U postgres -l
```

Si aparece `cnel_db`, ejecutar:

```bash
pg_dump -U postgres -d cnel_db > cnel_db_backup.sql
```

Después traer el archivo `cnel_db_backup.sql` a esta PC.
