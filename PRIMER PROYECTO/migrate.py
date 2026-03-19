"""
migrate.py — adapta la base de datos existente sin borrar datos.
Se ejecuta en cada arranque desde start.bat. Es idempotente: si ya
está migrado no hace nada.
"""
import sqlite3, sys, os
sys.path.insert(0, os.path.dirname(__file__))

DB = "tienda.db"

def columnas(cur, tabla):
    cur.execute(f"PRAGMA table_info({tabla})")
    return [r[1] for r in cur.fetchall()]

def tablas(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]

con = sqlite3.connect(DB)
cur = con.cursor()

# 1. Tabla departamentos
if "departamentos" not in tablas(cur):
    cur.execute("CREATE TABLE departamentos (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE)")
    print("Tabla departamentos creada")

# 2. Columna telefono en clientes
if "clientes" in tablas(cur) and "telefono" not in columnas(cur, "clientes"):
    cur.execute("ALTER TABLE clientes ADD COLUMN telefono TEXT DEFAULT ''")
    print("clientes.telefono añadida")

# 3. Columnas nuevas en operarios
if "operarios" in tablas(cur):
    cols = columnas(cur, "operarios")
    if "telefono" not in cols:
        cur.execute("ALTER TABLE operarios ADD COLUMN telefono TEXT DEFAULT ''")
        print("operarios.telefono añadida")
    if "departamento_id" not in cols:
        cur.execute("ALTER TABLE operarios ADD COLUMN departamento_id INTEGER REFERENCES departamentos(id)")
        print("operarios.departamento_id añadida")

# 4. Migrar departamentos desde strings existentes en operarios
cur.execute("SELECT DISTINCT departamento FROM operarios WHERE departamento IS NOT NULL AND departamento != ''")
for (nombre,) in cur.fetchall():
    cur.execute("INSERT OR IGNORE INTO departamentos (nombre) VALUES (?)", (nombre,))

# 5. Actualizar departamento_id donde sea NULL usando el string
cur.execute("""
    UPDATE operarios SET departamento_id = (
        SELECT id FROM departamentos WHERE nombre = operarios.departamento
    )
    WHERE departamento_id IS NULL AND departamento IS NOT NULL AND departamento != ''
""")
print("Migración departamentos completada")

con.commit()
con.close()
print("Migración OK")

# ── Eliminar campo total de albaranes ─────────────────────────────────────────
con2 = sqlite3.connect(DB)
cur2 = con2.cursor()
cur2.execute("PRAGMA table_info(albaranes)")
cols = [r[1] for r in cur2.fetchall()]
if "total" in cols:
    print("Eliminando campo total de albaranes...")
    cur2.executescript("""
        BEGIN;
        CREATE TABLE albaranes_new (
            id          INTEGER PRIMARY KEY,
            numero      TEXT UNIQUE,
            fecha       DATETIME,
            cliente_id  INTEGER REFERENCES clientes(id),
            operario_id INTEGER REFERENCES operarios(id)
        );
        INSERT INTO albaranes_new (id, numero, fecha, cliente_id, operario_id)
            SELECT id, numero, fecha, cliente_id, operario_id FROM albaranes;
        DROP TABLE albaranes;
        ALTER TABLE albaranes_new RENAME TO albaranes;
        COMMIT;
    """)
    print("Campo total eliminado OK")
else:
    print("Campo total ya eliminado, nada que hacer")
con2.close()

# ── Nuevos campos en lineas_venta ─────────────────────────────────────────────
con3 = sqlite3.connect(DB)
cur3 = con3.cursor()
cur3.execute("PRAGMA table_info(lineas_venta)")
lv_cols = [r[1] for r in cur3.fetchall()]

nuevos = [
    ("departamento",       "TEXT DEFAULT ''"),
    ("tipo_pago",          "TEXT DEFAULT ''"),
    ("modificado_por",     "TEXT DEFAULT ''"),
    ("fecha_modificacion", "TEXT DEFAULT ''"),
]
for col, tipo in nuevos:
    if col not in lv_cols:
        cur3.execute(f"ALTER TABLE lineas_venta ADD COLUMN {col} {tipo}")
        print(f"lineas_venta.{col} añadida")
    else:
        print(f"lineas_venta.{col} ya existe")

con3.commit()
con3.close()

# ── Rellenar departamento vacío en lineas_venta históricas ────────────────────
con4 = sqlite3.connect(DB)
cur4 = con4.cursor()
cur4.execute("""
    UPDATE lineas_venta
    SET departamento = (
        SELECT COALESCE(d.nombre, o.departamento, '')
        FROM albaranes a
        JOIN operarios o ON a.operario_id = o.id
        LEFT JOIN departamentos d ON o.departamento_id = d.id
        WHERE a.id = lineas_venta.albaran_id
    )
    WHERE departamento IS NULL OR departamento = ''
""")
affected = con4.execute("SELECT changes()").fetchone()[0]
print(f"Departamento rellenado en {affected} líneas históricas")
con4.commit()
con4.close()

# ── Tablas de configuración ───────────────────────────────────────────────────
con5 = sqlite3.connect(DB)
cur5 = con5.cursor()
tabs5 = [r[0] for r in con5.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

if "configuracion_campos" not in tabs5:
    con5.execute("""
        CREATE TABLE configuracion_campos (
            id          INTEGER PRIMARY KEY,
            tabla       TEXT,
            nombre      TEXT,
            etiqueta    TEXT,
            tipo        TEXT DEFAULT 'texto',
            tipo_campo  TEXT DEFAULT 'volatil',
            activo      INTEGER DEFAULT 1,
            orden       INTEGER DEFAULT 0,
            opciones    TEXT DEFAULT '',
            es_estandar INTEGER DEFAULT 0
        )
    """)
    print("Tabla configuracion_campos creada")

if "configuracion_ventas" not in tabs5:
    con5.execute("""
        CREATE TABLE configuracion_ventas (
            id       INTEGER PRIMARY KEY,
            campo_id INTEGER REFERENCES configuracion_campos(id),
            activo   INTEGER DEFAULT 1,
            orden    INTEGER DEFAULT 0
        )
    """)
    print("Tabla configuracion_ventas creada")

# Insertar campos estándar si no existen
ESTANDAR = [
    # (tabla, nombre, etiqueta, tipo)
    ("clientes",     "codigo",      "Código",       "texto"),
    ("clientes",     "nombre",      "Nombre",       "texto"),
    ("clientes",     "telefono",    "Teléfono",     "texto"),
    ("clientes",     "email",       "Email",        "texto"),
    ("clientes",     "ciudad",      "Ciudad",       "texto"),
    ("articulos",    "codigo",      "Código",       "texto"),
    ("articulos",    "descripcion", "Descripción",  "texto"),
    ("articulos",    "categoria",   "Categoría",    "texto"),
    ("articulos",    "precio",      "Precio",       "numero"),
    ("operarios",    "numero",      "Número",       "texto"),
    ("operarios",    "nombre",      "Nombre",       "texto"),
    ("operarios",    "telefono",    "Teléfono",     "texto"),
    ("operarios",    "departamento","Departamento", "texto"),
    ("departamentos","nombre",      "Nombre",       "texto"),
]
for i, (tabla, nombre, etiqueta, tipo) in enumerate(ESTANDAR):
    existe = con5.execute(
        "SELECT id FROM configuracion_campos WHERE tabla=? AND nombre=? AND es_estandar=1",
        (tabla, nombre)
    ).fetchone()
    if not existe:
        con5.execute(
            "INSERT INTO configuracion_campos (tabla,nombre,etiqueta,tipo,tipo_campo,activo,orden,es_estandar) VALUES (?,?,?,?,'fijo',1,?,1)",
            (tabla, nombre, etiqueta, tipo, i)
        )
print("Campos estándar registrados")
con5.commit()
con5.close()

# ── Columna extra (JSON) en tablas maestras y lineas_venta ────────────────────
con6 = sqlite3.connect(DB)
for tabla in ['clientes','articulos','operarios','departamentos','lineas_venta']:
    cols6 = [r[1] for r in con6.execute(f"PRAGMA table_info({tabla})").fetchall()]
    if 'extra' not in cols6:
        con6.execute(f"ALTER TABLE {tabla} ADD COLUMN extra TEXT DEFAULT '{{}}'")
        print(f"{tabla}.extra añadida")
    else:
        print(f"{tabla}.extra ya existe")

# Añadir columnas fijas personalizadas que estén activas en configuracion_campos
rows6 = con6.execute(
    "SELECT tabla, nombre FROM configuracion_campos WHERE tipo_campo='fijo' AND es_estandar=0 AND activo=1"
).fetchall()
for tabla, nombre in rows6:
    cols6 = [r[1] for r in con6.execute(f"PRAGMA table_info({tabla})").fetchall()]
    if nombre not in cols6:
        con6.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} TEXT DEFAULT ''")
        print(f"{tabla}.{nombre} añadida (campo fijo personalizado)")
con6.commit()
con6.close()

# ── Renombrar tipo_campo: fijo→columna, volatil→json ─────────────────────────
con7 = sqlite3.connect(DB)
con7.execute("UPDATE configuracion_campos SET tipo_campo='columna' WHERE tipo_campo='fijo'")
con7.execute("UPDATE configuracion_campos SET tipo_campo='json' WHERE tipo_campo='volatil'")
print("Tipo_campo renombrado: fijo→columna, volatil→json")

# Borrar campo de test "zona_geografica" creado como ejemplo
con7.execute("DELETE FROM configuracion_ventas WHERE campo_id IN (SELECT id FROM configuracion_campos WHERE nombre='zona_geografica' AND es_estandar=0)")
con7.execute("DELETE FROM configuracion_campos WHERE nombre='zona_geografica' AND es_estandar=0")
print("Campo test zona_geografica eliminado")

# ── Tabla configuracion_parametros ────────────────────────────────────────────
tabs7 = [r[0] for r in con7.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
if "configuracion_parametros" not in tabs7:
    con7.execute("""
        CREATE TABLE configuracion_parametros (
            clave TEXT PRIMARY KEY,
            valor TEXT,
            etiqueta TEXT,
            descripcion TEXT
        )
    """)
    con7.execute("INSERT INTO configuracion_parametros VALUES ('max_columnas','5','Máx. columnas por tabla','Máximo de campos tipo Columna (columna real en BD) por tabla')")
    con7.execute("INSERT INTO configuracion_parametros VALUES ('max_json','10','Máx. campos JSON por tabla','Máximo de campos tipo JSON por tabla')")
    print("Tabla configuracion_parametros creada con valores por defecto")
else:
    print("configuracion_parametros ya existe")

con7.commit()
con7.close()

# ── Tabla perfiles_vista ──────────────────────────────────────────────────────
con8 = sqlite3.connect(DB)
tabs8 = [r[0] for r in con8.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
if "perfiles_vista" not in tabs8:
    con8.execute("""
        CREATE TABLE perfiles_vista (
            id          INTEGER PRIMARY KEY,
            pantalla    TEXT,
            operario_id INTEGER REFERENCES operarios(id),
            nombre      TEXT,
            config      TEXT DEFAULT '{}',
            creado      TEXT
        )
    """)
    print("Tabla perfiles_vista creada")
else:
    print("perfiles_vista ya existe")
con8.commit()
con8.close()
