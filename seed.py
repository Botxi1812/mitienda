import random, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from database import SessionLocal, engine
import models
models.Base.metadata.create_all(bind=engine)
db = SessionLocal()
if db.query(models.Operario).count() > 0:
    print("Base de datos ya tiene datos. Saltando seed.")
    db.close()
    sys.exit(0)
random.seed(42)

# Departamentos
depts = {}
for nombre in ["Ventas", "Comercial", "Distribucion"]:
    d = models.Departamento(nombre=nombre, datos=json.dumps({}))
    db.add(d); db.flush(); depts[nombre] = d.id
db.commit(); print("Departamentos OK")

# Operarios
operarios_seed = [
    ("OP-001", "Carlos Mendoza",   "Ventas"),
    ("OP-002", "Laura Fernandez",  "Ventas"),
    ("OP-003", "Javier Romero",    "Comercial"),
    ("OP-004", "Ana Garcia",       "Comercial"),
    ("OP-005", "Miguel Torres",    "Distribucion"),
]
for num, nombre, dept in operarios_seed:
    db.add(models.Operario(nombre=nombre, datos=json.dumps({"numero": num, "departamento": dept})))
db.commit(); print("Operarios OK")

# Clientes
aps = ["Garcia","Lopez","Martinez","Sanchez","Perez","Gomez","Fernandez","Diaz","Torres","Ruiz",
       "Hernandez","Jimenez","Moreno","Munoz","Alvarez","Romero","Alonso","Gutierrez","Navarro","Molina"]
nms = ["Ana","Luis","Maria","Carlos","Laura","Javier","Sofia","David","Elena","Miguel",
       "Paula","Antonio","Carmen","Alejandro","Isabel","Manuel","Lucia","Pedro","Cristina","Raul"]
cds = ["Barcelona","Madrid","Valencia","Sevilla","Bilbao","Zaragoza","Malaga","Alicante","Murcia","Palma"]
for i in range(1, 101):
    db.add(models.Cliente(
        nombre=f"{random.choice(nms)} {random.choice(aps)}",
        datos=json.dumps({"codigo": f"CLI-{i:03d}", "email": f"cliente{i:03d}@empresa.com", "ciudad": random.choice(cds)})
    ))
db.commit(); print("Clientes OK")

# Articulos
arts = {}
articulos_seed = [
    ("ART-001", "Laptop Pro 15",      "Electronica",    1299.99),
    ("ART-002", "Monitor UHD 27",     "Electronica",     449.00),
    ("ART-003", "Teclado Mecanico",   "Perifericos",      89.50),
    ("ART-004", "Raton Inalambrico",  "Perifericos",      45.00),
    ("ART-005", "Servidor Cloud L",   "Servicios",      2500.00),
    ("ART-006", "Silla Ergonomica",   "Mobiliario",      350.00),
    ("ART-007", "Auriculares BT",     "Perifericos",     129.00),
    ("ART-008", "Software ERP Suite", "Software",       4800.00),
    ("ART-009", "Impresora Laser",    "Perifericos",     299.00),
    ("ART-010", "Disco SSD 2TB",      "Almacenamiento",  189.00),
]
for cod, desc, cat, precio in articulos_seed:
    a = models.Articulo(nombre=desc, datos=json.dumps({"codigo": cod, "categoria": cat, "precio": precio}))
    db.add(a); db.flush(); arts[cod] = a
db.commit(); print("Articulos OK")

# Tabla definiciones
tablas = [
    models.TablaDefinicion(nombre="departamentos", etiqueta="Departamentos", etiqueta_singular="Departamento",
        icono="", ruta="departamentos", campo_principal="nombre",
        en_nav=1, orden_nav=4, en_venta_tipo="ninguno", en_filtros=0, es_sistema=1, activa=1),
    models.TablaDefinicion(nombre="clientes", etiqueta="Clientes", etiqueta_singular="Cliente",
        icono="", ruta="clientes", campo_principal="nombre", campo_secundario="codigo",
        en_nav=1, orden_nav=1, en_venta_tipo="selector", en_venta_requerido=1, en_filtros=1, es_sistema=1, activa=1),
    models.TablaDefinicion(nombre="articulos", etiqueta="Articulos", etiqueta_singular="Articulo",
        icono="", ruta="articulos", campo_principal="nombre", campo_secundario="codigo",
        en_nav=1, orden_nav=2, en_venta_tipo="lineas", en_filtros=1, es_sistema=1, activa=1),
    models.TablaDefinicion(nombre="operarios", etiqueta="Trabajadores", etiqueta_singular="Trabajador",
        icono="", ruta="trabajadores", campo_principal="nombre", campo_secundario="numero",
        en_nav=1, orden_nav=3, en_venta_tipo="ninguno", en_filtros=1, es_sistema=1, activa=1),
]
for t in tablas:
    db.add(t)
db.commit(); print("Tabla definiciones OK")

# Campos
campos = [
    models.CampoDefinicion(tabla="clientes",      nombre="nombre",    etiqueta="Nombre",    tipo="texto",  es_principal=1, es_requerido=1, orden=0, activo=1),
    models.CampoDefinicion(tabla="clientes",      nombre="codigo",    etiqueta="Codigo",    tipo="texto",  es_principal=0, es_requerido=0, orden=1, activo=1),
    models.CampoDefinicion(tabla="clientes",      nombre="email",     etiqueta="Email",     tipo="texto",  es_principal=0, es_requerido=0, orden=2, activo=1),
    models.CampoDefinicion(tabla="clientes",      nombre="ciudad",    etiqueta="Ciudad",    tipo="texto",  es_principal=0, es_requerido=0, orden=3, activo=1),
    models.CampoDefinicion(tabla="articulos",     nombre="nombre",    etiqueta="Nombre",    tipo="texto",  es_principal=1, es_requerido=1, orden=0, activo=1),
    models.CampoDefinicion(tabla="articulos",     nombre="codigo",    etiqueta="Codigo",    tipo="texto",  es_principal=0, es_requerido=0, orden=1, activo=1),
    models.CampoDefinicion(tabla="articulos",     nombre="categoria", etiqueta="Categoria", tipo="texto",  es_principal=0, es_requerido=0, orden=2, activo=1),
    models.CampoDefinicion(tabla="articulos",     nombre="precio",    etiqueta="Precio",    tipo="numero", es_principal=0, es_requerido=1, orden=3, activo=1),
    models.CampoDefinicion(tabla="operarios",     nombre="nombre",    etiqueta="Nombre",    tipo="texto",  es_principal=1, es_requerido=1, orden=0, activo=1),
    models.CampoDefinicion(tabla="operarios",     nombre="numero",    etiqueta="Numero",    tipo="texto",  es_principal=0, es_requerido=0, orden=1, activo=1),
    models.CampoDefinicion(tabla="departamentos", nombre="nombre",    etiqueta="Nombre",    tipo="texto",  es_principal=1, es_requerido=1, orden=0, activo=1),
]
for c in campos:
    db.add(c)
db.commit(); print("Campos definicion OK")

db.add(models.ConfiguracionParametro(clave="max_json", valor="15", etiqueta="Max campos JSON por tabla", descripcion=""))
db.commit(); print("Parametros OK")

print("\nBase de datos lista: 100 clientes, 10 articulos, 5 operarios, 3 departamentos.")
db.close()
