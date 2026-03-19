import random, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(models.Cliente).count() > 0:
    print("Base de datos ya tiene datos. Saltando seed.")
    db.close()
    sys.exit(0)

random.seed(42)

# Operarios
operarios_data = [
    ("OP-001", "Carlos Mendoza",   "Ventas"),
    ("OP-002", "Laura Fernández",  "Ventas"),
    ("OP-003", "Javier Romero",    "Comercial"),
    ("OP-004", "Ana García",       "Comercial"),
    ("OP-005", "Miguel Torres",    "Distribución"),
]
for num, nombre, dept in operarios_data:
    db.add(models.Operario(numero=num, nombre=nombre, departamento=dept))
db.commit()
print("Operarios OK")

# Clientes
apellidos = ["García","López","Martínez","Sánchez","Pérez","Gómez","Fernández","Díaz",
             "Torres","Ruiz","Hernández","Jiménez","Moreno","Muñoz","Álvarez","Romero",
             "Alonso","Gutiérrez","Navarro","Molina","Serrano","Ramírez","Suárez","Blanco",
             "Castro","Ortega","Delgado","Rubio","Ramos","Prieto"]
nombres_p = ["Ana","Luis","María","Carlos","Laura","Javier","Sofía","David","Elena","Miguel",
             "Paula","Antonio","Carmen","Alejandro","Isabel","Manuel","Lucía","Pedro","Cristina",
             "Raúl","Teresa","Sergio","Patricia","Roberto","Marta","Fernando","Beatriz","Alberto","Rosa","Daniel"]
ciudades = ["Barcelona","Madrid","Valencia","Sevilla","Bilbao","Zaragoza","Málaga","Alicante","Murcia","Palma"]

for i in range(1, 101):
    db.add(models.Cliente(
        codigo=f"CLI-{i:03d}",
        nombre=f"{random.choice(nombres_p)} {random.choice(apellidos)}",
        email=f"cliente{i:03d}@empresa.com",
        ciudad=random.choice(ciudades)
    ))
db.commit()
print("Clientes OK")

# Artículos
articulos_data = [
    ("ART-001", "Laptop Pro 15\"",      "Electrónica",    1299.99),
    ("ART-002", "Monitor UHD 27\"",     "Electrónica",     449.00),
    ("ART-003", "Teclado Mecánico",     "Periféricos",      89.50),
    ("ART-004", "Ratón Inalámbrico",    "Periféricos",      45.00),
    ("ART-005", "Servidor Cloud L",     "Servicios",      2500.00),
    ("ART-006", "Silla Ergonómica",     "Mobiliario",      350.00),
    ("ART-007", "Auriculares BT",       "Periféricos",     129.00),
    ("ART-008", "Software ERP Suite",   "Software",       4800.00),
    ("ART-009", "Impresora Láser",      "Periféricos",     299.00),
    ("ART-010", "Disco SSD 2TB",        "Almacenamiento",  189.00),
]
for cod, desc, cat, precio in articulos_data:
    db.add(models.Articulo(codigo=cod, descripcion=desc, categoria=cat, precio=precio))
db.commit()
print("Artículos OK")

# Precios especiales
clientes = db.query(models.Cliente).all()
art005 = db.query(models.Articulo).filter_by(codigo="ART-005").first()
art008 = db.query(models.Articulo).filter_by(codigo="ART-008").first()

seleccion_005 = random.sample(clientes, 30)
seleccion_008 = random.sample(clientes, 20)

for c in seleccion_005:
    db.add(models.PrecioEspecial(
        cliente_id=c.id, articulo_id=art005.id,
        precio=round(random.uniform(1800, 2400), 2)
    ))
for c in seleccion_008:
    db.add(models.PrecioEspecial(
        cliente_id=c.id, articulo_id=art008.id,
        precio=round(random.uniform(3500, 4600), 2)
    ))
db.commit()
print("Precios especiales OK")
print("\nBase de datos lista con 100 clientes, 10 artículos, 5 operarios.")
db.close()
