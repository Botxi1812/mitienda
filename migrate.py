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

def tablas_bd(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]

con = sqlite3.connect(DB)
cur = con.cursor()

# ── 1. Tabla departamentos ────────────────────────────────────────────────────
if "departamentos" not in tablas_bd(cur):
    cur.execute("CREATE TABLE departamentos (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE)")
    print("Tabla departamentos creada")

# ── 2. Columna telefono en clientes ──────────────────────────────────────────
if "clientes" in tablas_bd(cur) and "telefono" not in columnas(cur, "clientes"):
    cur.execute("ALTER TABLE clientes ADD COLUMN telefono TEXT DEFAULT ''")
    print("clientes.telefono añadida")

# ── 3. Columnas nuevas en operarios ──────────────────────────────────────────
if "operarios" in tablas_bd(cur):
    cols = columnas(cur, "operarios")
    if "telefono" not in cols:
        cur.execute("ALTER TABLE operarios ADD COLUMN telefono TEXT DEFAULT ''")
        print("operarios.telefono añadida")
    if "departamento_id" not in cols:
        cur.execute("ALTER TABLE operarios ADD COLUMN departamento_id INTEGER REFERENCES departamentos(id)")
        print("operarios.departamento_id añadida")

# ── 4. Migrar departamentos desde strings existentes en operarios ─────────────
cur.execute("SELECT DISTINCT departamento FROM operarios WHERE departamento IS NOT NULL AND departamento != ''")
for (nombre,) in cur.fetchall():
    cur.execute("INSERT OR IGNORE INTO departamentos (nombre) VALUES (?)", (nombre,))

# ── 5. Actualizar departamento_id donde sea NULL usando el string ─────────────
cur.execute("""
    UPDATE operarios SET departamento_id = (
        SELECT id FROM departamentos WHERE nombre = operarios.departamento
    )
    WHERE departamento_id IS NULL AND departamento IS NOT NULL AND departamento != ''
""")
print("Migración departamentos completada")

con.commit()
con.close()

# ── 6. Eliminar campo total de albaranes ──────────────────────────────────────
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

# ── 7. Nuevos campos en lineas_venta ─────────────────────────────────────────
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

# ── 8. Rellenar departamento vacío en lineas_venta históricas ─────────────────
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

# ── 9. Tablas de configuración ────────────────────────────────────────────────
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

# ── 10. Columna extra (JSON) en tablas maestras y lineas_venta ────────────────
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

# ── 11. Renombrar tipo_campo: fijo→columna, volatil→json ─────────────────────
con7 = sqlite3.connect(DB)
con7.execute("UPDATE configuracion_campos SET tipo_campo='columna' WHERE tipo_campo='fijo'")
con7.execute("UPDATE configuracion_campos SET tipo_campo='json' WHERE tipo_campo='volatil'")
print("Tipo_campo renombrado: fijo->columna, volatil->json")

# Borrar campo de test "zona_geografica" creado como ejemplo
con7.execute("DELETE FROM configuracion_ventas WHERE campo_id IN (SELECT id FROM configuracion_campos WHERE nombre='zona_geografica' AND es_estandar=0)")
con7.execute("DELETE FROM configuracion_campos WHERE nombre='zona_geografica' AND es_estandar=0")
print("Campo test zona_geografica eliminado")

# ── 12. Tabla configuracion_parametros ───────────────────────────────────────
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

# ── 13. Tabla perfiles_vista ──────────────────────────────────────────────────
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

# ── 14. tabla_definiciones — fuente única de verdad para catálogos ────────────
con9 = sqlite3.connect(DB)
tabs9 = [r[0] for r in con9.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

if "tabla_definiciones" not in tabs9:
    con9.execute("""
        CREATE TABLE tabla_definiciones (
            id                INTEGER PRIMARY KEY,
            nombre            TEXT UNIQUE NOT NULL,
            etiqueta          TEXT NOT NULL,
            etiqueta_singular TEXT NOT NULL,
            icono             TEXT DEFAULT '',
            ruta              TEXT DEFAULT '',
            padre_tabla       TEXT DEFAULT '',
            campo_padre_fk    TEXT DEFAULT '',
            tipo_relacion     TEXT DEFAULT 'libre',
            campo_principal   TEXT DEFAULT '',
            campo_secundario  TEXT DEFAULT '',
            en_nav            INTEGER DEFAULT 1,
            orden_nav         INTEGER DEFAULT 0,
            en_venta_requerido INTEGER DEFAULT 0,
            en_venta_tipo     TEXT DEFAULT 'ninguno',
            en_filtros        INTEGER DEFAULT 0,
            es_sistema        INTEGER DEFAULT 0,
            activa            INTEGER DEFAULT 1,
            extra             TEXT DEFAULT '{}'
        )
    """)
    print("Tabla tabla_definiciones creada")

    # Poblar con las 4 tablas sistema iniciales
    tablas_sistema = [
        # (nombre, etiqueta, etiqueta_singular, icono, ruta, padre_tabla, campo_padre_fk,
        #  tipo_relacion, campo_principal, campo_secundario,
        #  en_nav, orden_nav, en_venta_requerido, en_venta_tipo, en_filtros, es_sistema)
        ("clientes",     "Clientes",     "Cliente",     "\U0001f464", "",            "",          "",
         "libre",        "nombre",       "codigo",
         1, 1, 1, "selector", 1, 1),
        ("articulos",    "Articulos",    "Articulo",    "\U0001f4e6", "",            "",          "",
         "libre",        "descripcion",  "codigo",
         1, 2, 1, "lineas",   0, 1),
        ("operarios",    "Trabajadores", "Trabajador",  "\U0001f477", "trabajadores","departamentos","departamento_id",
         "pertenece_a",  "nombre",       "numero",
         1, 3, 0, "ninguno",  1, 1),
        ("departamentos","Departamentos","Departamento","\U0001f3e2", "",            "",          "",
         "libre",        "nombre",       "",
         1, 4, 0, "ninguno",  0, 1),
    ]
    for row in tablas_sistema:
        con9.execute("""
            INSERT OR IGNORE INTO tabla_definiciones
            (nombre,etiqueta,etiqueta_singular,icono,ruta,padre_tabla,campo_padre_fk,
             tipo_relacion,campo_principal,campo_secundario,
             en_nav,orden_nav,en_venta_requerido,en_venta_tipo,en_filtros,es_sistema)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, row)
    print("Tablas sistema registradas en tabla_definiciones")
else:
    print("tabla_definiciones ya existe")

    # Añadir campo_padre_fk si falta (upgrade desde versión anterior)
    cols9 = [r[1] for r in con9.execute("PRAGMA table_info(tabla_definiciones)").fetchall()]
    if "campo_padre_fk" not in cols9:
        con9.execute("ALTER TABLE tabla_definiciones ADD COLUMN campo_padre_fk TEXT DEFAULT ''")
        con9.execute("UPDATE tabla_definiciones SET campo_padre_fk='departamento_id' WHERE nombre='departamentos'")
        print("tabla_definiciones.campo_padre_fk añadida")

con9.commit()
con9.close()

# ── 15. Nuevas columnas en configuracion_campos ───────────────────────────────
con10 = sqlite3.connect(DB)
cols10 = [r[1] for r in con10.execute("PRAGMA table_info(configuracion_campos)").fetchall()]

nuevas_cc = [
    ("es_requerido",      "INTEGER DEFAULT 0"),
    ("es_unico",          "INTEGER DEFAULT 0"),
    ("es_bloqueado_venta","INTEGER DEFAULT 0"),
    ("tabla_id",          "INTEGER REFERENCES tabla_definiciones(id)"),
]
for col, tipo in nuevas_cc:
    if col not in cols10:
        con10.execute(f"ALTER TABLE configuracion_campos ADD COLUMN {col} {tipo}")
        print(f"configuracion_campos.{col} añadida")

# Poblar es_bloqueado_venta para campos que son indispensables en ventas
BLOQUEADOS = {
    "clientes":     {"codigo", "nombre"},
    "articulos":    {"codigo", "descripcion"},
    "operarios":    {"numero", "nombre"},
    "departamentos":{"nombre"},
}
for tabla, campos in BLOQUEADOS.items():
    for campo in campos:
        con10.execute("""
            UPDATE configuracion_campos SET es_bloqueado_venta=1
            WHERE tabla=? AND nombre=? AND es_estandar=1
        """, (tabla, campo))

# Poblar tabla_id vinculando cada registro de configuracion_campos con su tabla_definiciones
con10.execute("""
    UPDATE configuracion_campos
    SET tabla_id = (SELECT id FROM tabla_definiciones WHERE nombre = configuracion_campos.tabla)
    WHERE tabla_id IS NULL
""")

print("configuracion_campos actualizada con es_bloqueado_venta y tabla_id")
con10.commit()
con10.close()

# ── 16. Tabla consultas_config — columnas dinámicas para consultas.html ───────
con11 = sqlite3.connect(DB)
tabs11 = [r[0] for r in con11.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

if "consultas_config" not in tabs11:
    con11.execute("""
        CREATE TABLE consultas_config (
            id           INTEGER PRIMARY KEY,
            campo        TEXT NOT NULL,
            etiqueta     TEXT NOT NULL,
            tabla_origen TEXT DEFAULT '',
            ancho_default INTEGER DEFAULT 120,
            en_default   INTEGER DEFAULT 1,
            orden        INTEGER DEFAULT 0,
            tipo_render  TEXT DEFAULT '',
            es_sistema   INTEGER DEFAULT 0,
            activa       INTEGER DEFAULT 1
        )
    """)
    print("Tabla consultas_config creada")

    # Las 17 columnas del sistema (derivadas de COLS_VISTA_DEFAULT hardcodeado)
    CONSULTAS_COLS = [
        # (campo, etiqueta, tabla_origen, ancho, en_default, orden, tipo_render, es_sistema)
        ("albaran",          "Albarán",       "albaranes",    90,  1,  0, "bold",          1),
        ("fecha",            "Fecha",          "albaranes",   130,  1,  1, "",              1),
        ("operario_num",     "Nº Op.",         "operarios",    55,  1,  2, "",              1),
        ("operario",         "Operario",       "operarios",   120,  1,  3, "",              1),
        ("departamento",     "Depto.",         "operarios",   100,  1,  4, "",              1),
        ("cliente_cod",      "Cód. Cliente",   "clientes",     90,  1,  5, "",              1),
        ("cliente",          "Cliente",        "clientes",    140,  1,  6, "bold",          1),
        ("ciudad",           "Ciudad",         "clientes",    100,  1,  7, "",              1),
        ("articulo_cod",     "Cód. Art.",      "articulos",    80,  1,  8, "",              1),
        ("articulo",         "Artículo",       "articulos",   150,  1,  9, "",              1),
        ("cantidad",         "Cant.",           "lineas_venta", 60,  1, 10, "cantidad",      1),
        ("precio_unitario",  "Precio unit.",   "lineas_venta",100,  1, 11, "moneda",        1),
        ("importe",          "Importe",        "lineas_venta",100,  1, 12, "importe",       1),
        ("tipo_pago",        "Pago",           "lineas_venta", 80,  1, 13, "",              1),
        ("especial",         "Precio",         "lineas_venta", 80,  1, 14, "badge_especial",1),
        ("modificado_por",   "Modificado por", "lineas_venta",110,  1, 15, "subdued",       1),
        ("fecha_modificacion","Fecha mod.",    "lineas_venta",120,  1, 16, "subdued",       1),
    ]
    for row in CONSULTAS_COLS:
        con11.execute("""
            INSERT INTO consultas_config
            (campo,etiqueta,tabla_origen,ancho_default,en_default,orden,tipo_render,es_sistema)
            VALUES (?,?,?,?,?,?,?,?)
        """, row)
    print("Columnas sistema registradas en consultas_config")
else:
    print("consultas_config ya existe")

con11.commit()
con11.close()

# ── 17. Corregir padre_tabla / campo_padre_fk en tabla_definiciones ───────────
# operarios pertenece_a departamentos (operarios.departamento_id -> departamentos.id)
# departamentos es tabla raiz sin padre
con12 = sqlite3.connect(DB)
con12.execute("""
    UPDATE tabla_definiciones SET padre_tabla='departamentos', campo_padre_fk='departamento_id'
    WHERE nombre='operarios'
""")
con12.execute("""
    UPDATE tabla_definiciones SET padre_tabla='', campo_padre_fk=''
    WHERE nombre='departamentos'
""")
con12.commit()
con12.close()

print("\nMigracion completa OK")
