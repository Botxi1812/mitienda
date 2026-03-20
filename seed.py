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
for nombre in ["Ventas","Comercial","Distribución"]:
    d = models.Departamento(nombre=nombre, datos=json.dumps({}))
    db.add(d); db.flush(); depts[nombre] = d.id
db.commit(); print("Departamentos OK")
# Operarios
for num,nombre,dept in [("OP-001","Carlos Mendoza","Ventas"),("OP-002","Laura Fernández","Ventas"),("OP-003","Javier Romero","Comercial"),("OP-004","Ana García","Comercial"),("OP-005","Miguel Torres","Distribución")]:
    db.add(models.Operario(nombre=nombre,departamento_id=depts[dept],datos=json.dumps({"numero":num})))
db.commit(); print("Operarios OK")
# Clientes
aps=["García","López","Martínez","Sánchez","Pérez","Gómez","Fernández","Díaz","Torres","Ruiz","Hernández","Jiménez","Moreno","Muñoz","Álvarez","Romero","Alonso","Gutiérrez","Navarro","Molina"]
nms=["Ana","Luis","María","Carlos","Laura","Javier","Sofía","David","Elena","Miguel","Paula","Antonio","Carmen","Alejandro","Isabel","Manuel","Lucía","Pedro","Cristina","Raúl"]
cds=["Barcelona","Madrid","Valencia","Sevilla","Bilbao","Zaragoza","Málaga","Alicante","Murcia","Palma"]
for i in range(1,101):
    db.add(models.Cliente(nombre=f"{random.choice(nms)} {random.choice(aps)}",datos=json.dumps({"codigo":f"CLI-{i:03d}","email":f"cliente{i:03d}@empresa.com","ciudad":random.choice(cds)})))
db.commit(); print("Clientes OK")
# Artículos
arts={}
for cod,desc,cat,precio in [("ART-001","Laptop Pro 15","Electrónica",1299.99),("ART-002","Monitor UHD 27","Electrónica",449.0),("ART-003","Teclado Mecánico","Periféricos",89.5),("ART-004","Ratón Inalámbrico","Periféricos",45.0),("ART-005","Servidor Cloud L","Servicios",2500.0),("ART-006","Silla Ergonómica","Mobiliario",350.0),("ART-007","Auriculares BT","Periféricos",129.0),("ART-008","Software ERP Suite","Software",4800.0),("ART-009","Impresora Láser","Periféricos",299.0),("ART-010","Disco SSD 2TB","Almacenamiento",189.0)]:
    a=models.Articulo(nombre=desc,datos=json.dumps({"codigo":cod,"categoria":cat,"precio":precio}))
    db.add(a); db.flush(); arts[cod]=a
db.commit(); print("Artículos OK")
# Precios especiales
clientes=db.query(models.Cliente).all()
for c in random.sample(clientes,30):
    db.add(models.PrecioEspecial(cliente_id=c.id,articulo_id=arts["ART-005"].id,precio=round(random.uniform(1800,2400),2)))
for c in random.sample(clientes,20):
    db.add(models.PrecioEspecial(cliente_id=c.id,articulo_id=arts["ART-008"].id,precio=round(random.uniform(3500,4600),2)))
db.commit(); print("Precios especiales OK")
# Tabla definiciones
for t in [
    models.TablaDefinicion(nombre="departamentos",etiqueta="Departamentos",etiqueta_singular="Departamento",icono="🏢",ruta="departamentos",campo_principal="nombre",en_nav=1,orden_nav=4,en_venta_tipo="ninguno",en_filtros=0,es_sistema=1,activa=1),
    models.TablaDefinicion(nombre="clientes",etiqueta="Clientes",etiqueta_singular="Cliente",icono="👤",ruta="clientes",campo_principal="nombre",campo_secundario="codigo",en_nav=1,orden_nav=1,en_venta_tipo="selector",en_venta_requerido=1,en_filtros=1,es_sistema=1,activa=1),
    models.TablaDefinicion(nombre="articulos",etiqueta="Artículos",etiqueta_singular="Artículo",icono="📦",ruta="articulos",campo_principal="nombre",campo_secundario="codigo",en_nav=1,orden_nav=2,en_venta_tipo="lineas",en_filtros=1,es_sistema=1,activa=1),
    models.TablaDefinicion(nombre="operarios",etiqueta="Trabajadores",etiqueta_singular="Trabajador",icono="👷",ruta="trabajadores",campo_principal="nombre",campo_secundario="numero",padre_tabla="departamentos",campo_padre_fk="departamento_id",en_nav=1,orden_nav=3,en_venta_tipo="ninguno",en_filtros=1,es_sistema=1,activa=1),
]:
    db.add(t)
db.commit(); print("Tabla definiciones OK")
# Campos
for c in [
    models.CampoDefinicion(tabla="clientes",nombre="nombre",etiqueta="Nombre",tipo="texto",es_principal=1,es_requerido=1,orden=0,activo=1),
    models.CampoDefinicion(tabla="clientes",nombre="codigo",etiqueta="Código",tipo="texto",es_principal=0,es_requerido=0,orden=1,activo=1),
    models.CampoDefinicion(tabla="clientes",nombre="email",etiqueta="Email",tipo="texto",es_principal=0,es_requerido=0,orden=2,activo=1),
    models.CampoDefinicion(tabla="clientes",nombre="ciudad",etiqueta="Ciudad",tipo="texto",es_principal=0,es_requerido=0,orden=3,activo=1),
    models.CampoDefinicion(tabla="articulos",nombre="nombre",etiqueta="Nombre",tipo="texto",es_principal=1,es_requerido=1,orden=0,activo=1),
    models.CampoDefinicion(tabla="articulos",nombre="codigo",etiqueta="Código",tipo="texto",es_principal=0,es_requerido=0,orden=1,activo=1),
    models.CampoDefinicion(tabla="articulos",nombre="categoria",etiqueta="Categoría",tipo="texto",es_principal=0,es_requerido=0,orden=2,activo=1),
    models.CampoDefinicion(tabla="articulos",nombre="precio",etiqueta="Precio",tipo="numero",es_principal=0,es_requerido=1,orden=3,activo=1),
    models.CampoDefinicion(tabla="operarios",nombre="nombre",etiqueta="Nombre",tipo="texto",es_principal=1,es_requerido=1,orden=0,activo=1),
    models.CampoDefinicion(tabla="operarios",nombre="numero",etiqueta="Número",tipo="texto",es_principal=0,es_requerido=0,orden=1,activo=1),
    models.CampoDefinicion(tabla="departamentos",nombre="nombre",etiqueta="Nombre",tipo="texto",es_principal=1,es_requerido=1,orden=0,activo=1),
]:
    db.add(c)
db.commit(); print("Campos definición OK")
db.add(models.ConfiguracionParametro(clave="max_json",valor="15",etiqueta="Máx. campos JSON por tabla",descripcion=""))
db.commit(); print("Parámetros OK")
print("\nBase de datos lista: 100 clientes, 10 artículos, 5 operarios, 3 departamentos.")
db.close()
