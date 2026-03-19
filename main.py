from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import models, database, json, re

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Mi Tienda")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Páginas ───────────────────────────────────────────────────────────────────
@app.get("/")
def root():               return FileResponse("static/pc/login.html")
@app.get("/ventas")
def ventas():             return FileResponse("static/pc/ventas.html")
@app.get("/consultas")
def consultas():          return FileResponse("static/pc/consultas.html")
@app.get("/clientes")
def clientes_page():      return FileResponse("static/pc/clientes.html")
@app.get("/trabajadores")
def trabajadores_page():  return FileResponse("static/pc/trabajadores.html")
@app.get("/articulos")
def articulos_page():     return FileResponse("static/pc/articulos.html")
@app.get("/departamentos")
def departamentos_page(): return FileResponse("static/pc/departamentos.html")
@app.get("/configuracion")
def configuracion_page(): return FileResponse("static/pc/configuracion.html")
@app.get("/movil")
def movil():              return FileResponse("static/movil/login.html")

# ── Helpers ───────────────────────────────────────────────────────────────────
def dept_nombre(op):
    if op.dept: return op.dept.nombre
    return op.departamento or ""

def parse_extra(val):
    if not val: return {}
    try: return json.loads(val)
    except: return {}

def dump_extra(d): return json.dumps(d, ensure_ascii=False)

# Campos mínimos para identificar una venta — siempre grabados, no configurables
CAMPOS_LOCKED_VENTA = {
    'clientes':     {'codigo', 'nombre'},
    'articulos':    {'codigo', 'descripcion'},
    'operarios':    {'numero', 'nombre'},
    'departamentos':{'nombre'},
}

def linea_dict(l):
    extra = parse_extra(getattr(l, 'extra', None))
    return {
        "id":              l.id,
        "cliente_id":      l.albaran.cliente_id,
        "albaran":         l.albaran.numero,
        "albaran_id":      l.albaran_id,
        "fecha":           l.albaran.fecha.strftime("%d/%m/%Y %H:%M"),
        "operario_num":    l.albaran.operario.numero,
        "operario":        l.albaran.operario.nombre,
        "departamento":    l.departamento or dept_nombre(l.albaran.operario),
        "cliente_cod":     l.albaran.cliente.codigo,
        "cliente":         l.albaran.cliente.nombre,
        "ciudad":          l.albaran.cliente.ciudad,
        "articulo_id":     l.articulo_id,
        "articulo_cod":    l.articulo.codigo,
        "articulo":        l.articulo.descripcion,
        "cantidad":        l.cantidad,
        "precio_unitario": l.precio_unitario,
        "importe":         l.importe,
        "especial":        l.es_precio_especial == 1,
        "tipo_pago":       l.tipo_pago or "",
        "modificado_por":  l.modificado_por or "",
        "fecha_modificacion": l.fecha_modificacion or "",
        **extra
    }

def campos_extra_tabla(db, tabla):
    """Devuelve campos personalizados activos de una tabla."""
    rows = db.execute(text(
        "SELECT nombre, etiqueta, tipo, tipo_campo, opciones FROM configuracion_campos "
        "WHERE tabla=:t AND activo=1 AND es_estandar=0 ORDER BY orden"
    ), {"t": tabla}).fetchall()
    return [{"nombre": r[0], "etiqueta": r[1], "tipo": r[2],
             "tipo_campo": r[3], "opciones": r[4] or ""} for r in rows]

def row_to_dict_extra(row, campos_extra):
    """Extrae campos fijos y volátiles de un registro."""
    extra_json = parse_extra(getattr(row, 'extra', None))
    result = {}
    for c in campos_extra:
        if c['tipo_campo'] == 'fijo':
            result[c['nombre']] = getattr(row, c['nombre'], None) or ""
        else:
            result[c['nombre']] = extra_json.get(c['nombre'], "")
    return result

# ── API Catálogos ─────────────────────────────────────────────────────────────
@app.get("/api/operarios")
def get_operarios(db: Session = Depends(database.get_db)):
    campos = campos_extra_tabla(db, "operarios")
    ops = db.execute(text("SELECT * FROM operarios")).fetchall()
    result = []
    for o in db.query(models.Operario).all():
        d = {"id": o.id, "numero": o.numero, "nombre": o.nombre,
             "telefono": o.telefono or "",
             "departamento": dept_nombre(o),
             "departamento_id": o.departamento_id}
        d.update(row_to_dict_extra(o, campos))
        result.append(d)
    return result

@app.get("/api/clientes")
def get_clientes(db: Session = Depends(database.get_db)):
    campos = campos_extra_tabla(db, "clientes")
    result = []
    for c in db.query(models.Cliente).order_by(models.Cliente.nombre).all():
        d = {"id": c.id, "codigo": c.codigo, "nombre": c.nombre,
             "email": c.email or "", "telefono": c.telefono or "", "ciudad": c.ciudad or ""}
        d.update(row_to_dict_extra(c, campos))
        result.append(d)
    return result

@app.get("/api/articulos")
def get_articulos(db: Session = Depends(database.get_db)):
    campos = campos_extra_tabla(db, "articulos")
    result = []
    for a in db.query(models.Articulo).order_by(models.Articulo.descripcion).all():
        d = {"id": a.id, "codigo": a.codigo, "descripcion": a.descripcion,
             "categoria": a.categoria, "precio": a.precio}
        d.update(row_to_dict_extra(a, campos))
        result.append(d)
    return result

@app.get("/api/departamentos")
def get_departamentos(db: Session = Depends(database.get_db)):
    campos = campos_extra_tabla(db, "departamentos")
    result = []
    for d in db.query(models.Departamento).order_by(models.Departamento.nombre).all():
        row = {"id": d.id, "nombre": d.nombre}
        row.update(row_to_dict_extra(d, campos))
        result.append(row)
    return result

@app.get("/api/campos_extra/{tabla}")
def get_campos_extra(tabla: str, db: Session = Depends(database.get_db)):
    return campos_extra_tabla(db, tabla)

@app.get("/api/precio/{cliente_id}/{articulo_id}")
def get_precio(cliente_id: int, articulo_id: int, db: Session = Depends(database.get_db)):
    esp = db.query(models.PrecioEspecial).filter_by(
        cliente_id=cliente_id, articulo_id=articulo_id).first()
    if esp: return {"precio": esp.precio, "especial": True}
    art = db.query(models.Articulo).get(articulo_id)
    if not art: raise HTTPException(404, "Artículo no encontrado")
    return {"precio": art.precio, "especial": False}

# ── API Ventas ────────────────────────────────────────────────────────────────
class LineaIn(BaseModel):
    articulo_id: int
    cantidad: float
    precio_unitario: float
    es_precio_especial: bool
    tipo_pago: Optional[str] = ""
    extra: Optional[Dict[str, Any]] = {}

class AlbaranIn(BaseModel):
    cliente_id: int
    operario_id: int
    lineas: List[LineaIn]

@app.post("/api/albaranes")
def crear_albaran(data: AlbaranIn, db: Session = Depends(database.get_db)):
    operario = db.query(models.Operario).get(data.operario_id)
    if not operario: raise HTTPException(404, "Operario no encontrado")
    cliente = db.query(models.Cliente).get(data.cliente_id)
    if not cliente: raise HTTPException(404, "Cliente no encontrado")

    # Cargar campos estándar configurables con su estado en_ventas
    snap_rows = db.execute(text("""
        SELECT c.nombre, c.tabla, COALESCE(cv.activo, 1) as en_ventas
        FROM configuracion_campos c
        LEFT JOIN configuracion_ventas cv ON cv.campo_id = c.id
        WHERE c.es_estandar=1 AND c.activo=1
    """)).fetchall()
    # Filtrar los bloqueados: sólo procesar los configurables
    snap_config = [(n, t, bool(ev)) for n, t, ev in snap_rows
                   if n not in CAMPOS_LOCKED_VENTA.get(t, set())]

    dept = dept_nombre(operario)
    n = db.query(models.Albaran).count() + 1
    albaran = models.Albaran(
        numero=f"ALB-{n:06d}",
        cliente_id=data.cliente_id,
        operario_id=data.operario_id,
        fecha=datetime.now()
    )
    db.add(albaran); db.flush()
    for l in data.lineas:
        articulo = db.query(models.Articulo).get(l.articulo_id)
        extra = dict(l.extra or {})

        # Snapshot de campos estándar configurables en el momento de la venta
        for nombre, tabla, en_ventas in snap_config:
            if tabla == 'clientes':   entity = cliente
            elif tabla == 'articulos': entity = articulo
            elif tabla == 'operarios': entity = operario
            else: continue  # departamentos: no tienen campos configurables actualmente
            if en_ventas:
                val = getattr(entity, nombre, None)
                extra[nombre] = str(val) if val is not None else ''
            else:
                extra[nombre] = ''  # Vacío explícito = campo desactivado en configuración

        db.add(models.LineaVenta(
            albaran_id=albaran.id,
            articulo_id=l.articulo_id,
            cantidad=l.cantidad,
            precio_unitario=l.precio_unitario,
            importe=round(l.cantidad * l.precio_unitario, 2),
            es_precio_especial=1 if l.es_precio_especial else 0,
            departamento=dept,
            tipo_pago=l.tipo_pago or "",
            extra=dump_extra(extra)
        ))
    db.commit()
    return {"ok": True, "numero": albaran.numero}

@app.get("/api/ventas/buscar_campo")
def buscar_por_campo(
    campo: str, valor: str,
    db: Session = Depends(database.get_db)
):
    import re
    if not re.match(r'^[a-z_][a-z0-9_]*$', campo):
        raise HTTPException(400, "Campo no válido")
    # Buscar en JSON extra (LIKE funciona en todas las versiones de SQLite)
    rows_json = db.execute(text(
        "SELECT DISTINCT lv.id FROM lineas_venta lv "
        "WHERE lv.extra LIKE :vlike ORDER BY lv.albaran_id DESC LIMIT 500"
    ), {"vlike": f'%"{campo}": "{valor}"%'}).fetchall()
    # También buscar en columna real si existe
    existing_cols = {r[1] for r in db.execute(text("PRAGMA table_info(lineas_venta)"))}
    ids = {r[0] for r in rows_json}
    if campo in existing_cols:
        rows_col = db.execute(text(
            f"SELECT DISTINCT lv.id FROM lineas_venta lv WHERE lv.{campo} = :v LIMIT 500"
        ), {"v": valor}).fetchall()
        ids |= {r[0] for r in rows_col}
    if not ids:
        return []
    resultado = db.query(models.LineaVenta).filter(models.LineaVenta.id.in_(list(ids))).all()
    return [linea_dict(l) for l in resultado]

@app.get("/api/ventas")
def get_ventas(
    fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
    operario_id: Optional[int] = None, cliente_id: Optional[int] = None,
    articulo_id: Optional[int] = None, db: Session = Depends(database.get_db)
):
    q = (db.query(models.LineaVenta).join(models.Albaran)
         .join(models.Cliente,  models.Albaran.cliente_id  == models.Cliente.id)
         .join(models.Operario, models.Albaran.operario_id == models.Operario.id)
         .join(models.Articulo, models.LineaVenta.articulo_id == models.Articulo.id))
    if fecha_desde: q = q.filter(models.Albaran.fecha >= fecha_desde)
    if fecha_hasta: q = q.filter(models.Albaran.fecha <= fecha_hasta + " 23:59:59")
    if operario_id: q = q.filter(models.Albaran.operario_id == operario_id)
    if cliente_id:  q = q.filter(models.Albaran.cliente_id  == cliente_id)
    if articulo_id: q = q.filter(models.LineaVenta.articulo_id == articulo_id)
    return [linea_dict(l) for l in q.order_by(models.Albaran.fecha.desc()).limit(1000).all()]

# ── API Edición multilinea ────────────────────────────────────────────────────
class LineaPatch(BaseModel):
    id: int
    articulo_id: int
    cantidad: float
    precio_unitario: float
    tipo_pago: Optional[str] = ""
    modificado_por: str

@app.patch("/api/lineas")
def editar_lineas(cambios: List[LineaPatch], db: Session = Depends(database.get_db)):
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    for c in cambios:
        l = db.query(models.LineaVenta).get(c.id)
        if not l: continue
        if l.articulo_id != c.articulo_id:
            esp = db.query(models.PrecioEspecial).filter_by(
                cliente_id=l.albaran.cliente_id, articulo_id=c.articulo_id).first()
            l.articulo_id = c.articulo_id
            l.es_precio_especial = 1 if esp else 0
        l.cantidad = c.cantidad
        l.precio_unitario = c.precio_unitario
        l.importe = round(c.cantidad * c.precio_unitario, 2)
        l.tipo_pago = c.tipo_pago or ""
        l.modificado_por = c.modificado_por
        l.fecha_modificacion = ahora
    db.commit()
    return {"ok": True, "actualizadas": len(cambios)}

@app.delete("/api/lineas/{linea_id}")
def eliminar_linea(linea_id: int, modificado_por: str = "", db: Session = Depends(database.get_db)):
    l = db.query(models.LineaVenta).get(linea_id)
    if not l: raise HTTPException(404, "Línea no encontrada")
    albaran_id = l.albaran_id
    db.delete(l); db.flush()
    restantes = db.query(models.LineaVenta).filter_by(albaran_id=albaran_id).count()
    if restantes == 0:
        alb = db.query(models.Albaran).get(albaran_id)
        if alb: db.delete(alb)
    db.commit()
    return {"ok": True, "albaran_borrado": restantes == 0}

# ── API CRUD genérico con extra ───────────────────────────────────────────────
def guardar_extra(db, tabla, row_id, datos_extra, campos_def):
    """Guarda campos fijos en columnas y volátiles en JSON extra."""
    fijos = {c['nombre']: datos_extra.get(c['nombre'], "")
             for c in campos_def if c['tipo_campo'] == 'fijo'}
    volatiles = {c['nombre']: datos_extra.get(c['nombre'], "")
                 for c in campos_def if c['tipo_campo'] == 'volatil'}
    if fijos:
        sets = ", ".join(f"{k}=:{k}" for k in fijos)
        db.execute(text(f"UPDATE {tabla} SET {sets} WHERE id=:id"),
                   {**fijos, "id": row_id})
    if volatiles:
        current = db.execute(text(f"SELECT extra FROM {tabla} WHERE id=:id"),
                             {"id": row_id}).fetchone()
        existing = parse_extra(current[0] if current else None)
        existing.update(volatiles)
        db.execute(text(f"UPDATE {tabla} SET extra=:e WHERE id=:id"),
                   {"e": dump_extra(existing), "id": row_id})

# ── API CRUD Clientes ─────────────────────────────────────────────────────────
class ClienteIn(BaseModel):
    codigo: str; nombre: str
    email: Optional[str] = ""; telefono: Optional[str] = ""; ciudad: Optional[str] = ""
    extra: Optional[Dict[str, Any]] = {}

@app.post("/api/clientes")
def crear_cliente(data: ClienteIn, db: Session = Depends(database.get_db)):
    if db.query(models.Cliente).filter_by(codigo=data.codigo).first():
        raise HTTPException(400, "Código ya existe")
    c = models.Cliente(codigo=data.codigo, nombre=data.nombre,
                       email=data.email, telefono=data.telefono, ciudad=data.ciudad)
    db.add(c); db.commit(); db.refresh(c)
    if data.extra:
        campos = campos_extra_tabla(db, "clientes")
        guardar_extra(db, "clientes", c.id, data.extra, campos)
        db.commit()
    return {"ok": True, "id": c.id}

@app.put("/api/clientes/{cid}")
def actualizar_cliente(cid: int, data: ClienteIn, db: Session = Depends(database.get_db)):
    c = db.query(models.Cliente).get(cid)
    if not c: raise HTTPException(404, "No encontrado")
    if db.query(models.Cliente).filter(models.Cliente.codigo==data.codigo,
                                        models.Cliente.id!=cid).first():
        raise HTTPException(400, "Código ya existe en otro cliente")
    c.codigo=data.codigo; c.nombre=data.nombre; c.email=data.email
    c.telefono=data.telefono; c.ciudad=data.ciudad
    db.commit()
    if data.extra is not None:
        campos = campos_extra_tabla(db, "clientes")
        guardar_extra(db, "clientes", cid, data.extra, campos)
        db.commit()
    return {"ok": True}

# ── API CRUD Departamentos ────────────────────────────────────────────────────
class DepartamentoIn(BaseModel):
    nombre: str
    extra: Optional[Dict[str, Any]] = {}

@app.post("/api/departamentos")
def crear_departamento(data: DepartamentoIn, db: Session = Depends(database.get_db)):
    if db.query(models.Departamento).filter_by(nombre=data.nombre).first():
        raise HTTPException(400, "Departamento ya existe")
    d = models.Departamento(nombre=data.nombre)
    db.add(d); db.commit(); db.refresh(d)
    if data.extra:
        campos = campos_extra_tabla(db, "departamentos")
        guardar_extra(db, "departamentos", d.id, data.extra, campos)
        db.commit()
    return {"ok": True, "id": d.id}

@app.put("/api/departamentos/{did}")
def actualizar_departamento(did: int, data: DepartamentoIn, db: Session = Depends(database.get_db)):
    d = db.query(models.Departamento).get(did)
    if not d: raise HTTPException(404, "No encontrado")
    if db.query(models.Departamento).filter(models.Departamento.nombre==data.nombre,
                                             models.Departamento.id!=did).first():
        raise HTTPException(400, "Nombre ya existe")
    d.nombre = data.nombre; db.commit()
    if data.extra is not None:
        campos = campos_extra_tabla(db, "departamentos")
        guardar_extra(db, "departamentos", did, data.extra, campos)
        db.commit()
    return {"ok": True}

# ── API CRUD Trabajadores ─────────────────────────────────────────────────────
class OperarioIn(BaseModel):
    numero: str; nombre: str
    telefono: Optional[str] = ""; departamento_id: Optional[int] = None
    extra: Optional[Dict[str, Any]] = {}

@app.post("/api/trabajadores")
def crear_trabajador(data: OperarioIn, db: Session = Depends(database.get_db)):
    if db.query(models.Operario).filter_by(numero=data.numero).first():
        raise HTTPException(400, "Número ya existe")
    dn = ""
    if data.departamento_id:
        d = db.query(models.Departamento).get(data.departamento_id)
        if d: dn = d.nombre
    o = models.Operario(numero=data.numero, nombre=data.nombre,
        telefono=data.telefono or "", departamento_id=data.departamento_id, departamento=dn)
    db.add(o); db.commit(); db.refresh(o)
    if data.extra:
        campos = campos_extra_tabla(db, "operarios")
        guardar_extra(db, "operarios", o.id, data.extra, campos)
        db.commit()
    return {"ok": True, "id": o.id}

@app.put("/api/trabajadores/{oid}")
def actualizar_trabajador(oid: int, data: OperarioIn, db: Session = Depends(database.get_db)):
    o = db.query(models.Operario).get(oid)
    if not o: raise HTTPException(404, "No encontrado")
    if db.query(models.Operario).filter(models.Operario.numero==data.numero,
                                         models.Operario.id!=oid).first():
        raise HTTPException(400, "Número ya existe en otro trabajador")
    dn = ""
    if data.departamento_id:
        d = db.query(models.Departamento).get(data.departamento_id)
        if d: dn = d.nombre
    o.numero=data.numero; o.nombre=data.nombre; o.telefono=data.telefono or ""
    o.departamento_id=data.departamento_id; o.departamento=dn
    db.commit()
    if data.extra is not None:
        campos = campos_extra_tabla(db, "operarios")
        guardar_extra(db, "operarios", oid, data.extra, campos)
        db.commit()
    return {"ok": True}

# ── API CRUD Artículos ────────────────────────────────────────────────────────
class ArticuloIn(BaseModel):
    codigo: str; descripcion: str
    categoria: Optional[str] = ""; precio: float
    extra: Optional[Dict[str, Any]] = {}

@app.post("/api/articulos")
def crear_articulo(data: ArticuloIn, db: Session = Depends(database.get_db)):
    if db.query(models.Articulo).filter_by(codigo=data.codigo).first():
        raise HTTPException(400, "Código ya existe")
    a = models.Articulo(codigo=data.codigo, descripcion=data.descripcion,
                        categoria=data.categoria, precio=data.precio)
    db.add(a); db.commit(); db.refresh(a)
    if data.extra:
        campos = campos_extra_tabla(db, "articulos")
        guardar_extra(db, "articulos", a.id, data.extra, campos)
        db.commit()
    return {"ok": True, "id": a.id}

@app.put("/api/articulos/{aid}")
def actualizar_articulo(aid: int, data: ArticuloIn, db: Session = Depends(database.get_db)):
    a = db.query(models.Articulo).get(aid)
    if not a: raise HTTPException(404, "No encontrado")
    if db.query(models.Articulo).filter(models.Articulo.codigo==data.codigo,
                                         models.Articulo.id!=aid).first():
        raise HTTPException(400, "Código ya existe en otro artículo")
    a.codigo=data.codigo; a.descripcion=data.descripcion
    a.categoria=data.categoria; a.precio=data.precio
    db.commit()
    if data.extra is not None:
        campos = campos_extra_tabla(db, "articulos")
        guardar_extra(db, "articulos", aid, data.extra, campos)
        db.commit()
    return {"ok": True}

# ── API Configuración ─────────────────────────────────────────────────────────
LIMITES = {"columna": 5, "json": 10}
TABLAS  = ["clientes", "articulos", "operarios", "departamentos"]

@app.get("/api/config/campos")
def get_campos(db: Session = Depends(database.get_db)):
    # Auto-inicializar configuracion_ventas para campos estándar NO bloqueados
    # (primera vez que se abre la pantalla de config, se marcan como activos por defecto)
    sin_cv = db.execute(text("""
        SELECT c.id, c.tabla, c.nombre FROM configuracion_campos c
        LEFT JOIN configuracion_ventas cv ON cv.campo_id = c.id
        WHERE c.es_estandar=1 AND c.activo=1 AND cv.id IS NULL
    """)).fetchall()
    inserted = 0
    for campo_id, tabla, nombre in sin_cv:
        if nombre not in CAMPOS_LOCKED_VENTA.get(tabla, set()):
            orden = db.execute(text("SELECT COALESCE(MAX(orden),0)+1 FROM configuracion_ventas")).scalar()
            db.execute(text("INSERT INTO configuracion_ventas (campo_id,activo,orden) VALUES (:c,1,:o)"),
                       {"c": campo_id, "o": orden})
            inserted += 1
    if inserted:
        db.commit()

    rows = db.execute(text("""
        SELECT c.id, c.tabla, c.nombre, c.etiqueta, c.tipo, c.tipo_campo,
               c.activo, c.orden, c.opciones, c.es_estandar,
               COALESCE(cv.activo, 0) as en_ventas,
               cv.id as cv_id, cv.orden as ventas_orden
        FROM configuracion_campos c
        LEFT JOIN configuracion_ventas cv ON cv.campo_id = c.id
        ORDER BY c.tabla, c.orden
    """)).fetchall()
    result = {}
    for r in rows:
        t = r[1]
        if t not in result: result[t] = []
        result[t].append({
            "id": r[0], "tabla": r[1], "nombre": r[2], "etiqueta": r[3],
            "tipo": r[4], "tipo_campo": r[5], "activo": bool(r[6]),
            "orden": r[7], "opciones": r[8] or "", "es_estandar": bool(r[9]),
            "en_ventas": bool(r[10]), "cv_id": r[11], "ventas_orden": r[12] or 0
        })
    return result

@app.get("/api/config/ventas")
def get_config_ventas(db: Session = Depends(database.get_db)):
    rows = db.execute(text("""
        SELECT c.id, c.tabla, c.nombre, c.etiqueta, c.tipo, c.tipo_campo, cv.orden
        FROM configuracion_ventas cv
        JOIN configuracion_campos c ON c.id = cv.campo_id
        WHERE cv.activo = 1
        ORDER BY cv.orden
    """)).fetchall()
    return [{"id": r[0], "tabla": r[1], "nombre": r[2], "etiqueta": r[3],
             "tipo": r[4], "tipo_campo": r[5]} for r in rows]

class CampoIn(BaseModel):
    tabla: str; etiqueta: str
    tipo: Optional[str] = "texto"; tipo_campo: str
    opciones: Optional[str] = ""

@app.post("/api/config/campos")
def crear_campo(data: CampoIn, db: Session = Depends(database.get_db)):
    if data.tabla not in TABLAS: raise HTTPException(400, "Tabla no válida")
    if data.tipo_campo not in ("columna","json"): raise HTTPException(400, "tipo_campo inválido")
    max_col  = int(db.execute(text("SELECT valor FROM configuracion_parametros WHERE clave='max_columnas'")).scalar() or 5)
    max_json = int(db.execute(text("SELECT valor FROM configuracion_parametros WHERE clave='max_json'")).scalar() or 10)
    # Columna BD: cuentan activas Y archivadas (siguen en BD), no estándar
    # JSON: solo cuentan las activas (archivadas no ocupan esquema)
    if data.tipo_campo == "columna":
        cuenta = db.execute(text(
            "SELECT COUNT(*) FROM configuracion_campos WHERE tabla=:t AND tipo_campo='columna' AND es_estandar=0"
        ), {"t": data.tabla}).scalar()
        limite = max_col
    else:
        cuenta = db.execute(text(
            "SELECT COUNT(*) FROM configuracion_campos WHERE tabla=:t AND tipo_campo='json' AND activo=1 AND es_estandar=0"
        ), {"t": data.tabla}).scalar()
        limite = max_json
    if cuenta >= limite:
        raise HTTPException(400, f"Límite de {limite} campos {data.tipo_campo} alcanzado para esta tabla")
    nombre = data.etiqueta.lower().strip()
    for a,b in [(" ","_"),("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        nombre = nombre.replace(a,b)
    nombre = ''.join(c for c in nombre if c.isalnum() or c=='_')
    if db.execute(text("SELECT id FROM configuracion_campos WHERE tabla=:t AND nombre=:n"),
                  {"t": data.tabla, "n": nombre}).fetchone():
        raise HTTPException(400, "Ya existe un campo con ese nombre")
    orden = db.execute(text("SELECT COALESCE(MAX(orden),0)+1 FROM configuracion_campos WHERE tabla=:t"),
                       {"t": data.tabla}).scalar()
    db.execute(text("""
        INSERT INTO configuracion_campos (tabla,nombre,etiqueta,tipo,tipo_campo,activo,orden,opciones,es_estandar)
        VALUES (:tabla,:nombre,:etiqueta,:tipo,:tipo_campo,1,:orden,:opciones,0)
    """), {"tabla":data.tabla,"nombre":nombre,"etiqueta":data.etiqueta,
           "tipo":data.tipo,"tipo_campo":data.tipo_campo,"orden":orden,"opciones":data.opciones or ""})
    # Si es campo columna, añadir columna real a la tabla en BD
    if data.tipo_campo == "columna":
        existing = [r[1] for r in db.execute(text(f"PRAGMA table_info({data.tabla})"))]
        if nombre not in existing:
            db.execute(text(f"ALTER TABLE {data.tabla} ADD COLUMN {nombre} TEXT DEFAULT ''"))
    db.commit()
    return {"ok": True}

@app.patch("/api/config/campos/{campo_id}/archivar")
def archivar_campo(campo_id: int, db: Session = Depends(database.get_db)):
    row = db.execute(text("SELECT es_estandar FROM configuracion_campos WHERE id=:id"),
                     {"id": campo_id}).fetchone()
    if not row: raise HTTPException(404, "Campo no encontrado")
    if row[0]: raise HTTPException(400, "Los campos estándar no se pueden archivar")
    db.execute(text("UPDATE configuracion_campos SET activo=0 WHERE id=:id"), {"id": campo_id})
    db.execute(text("UPDATE configuracion_ventas SET activo=0 WHERE campo_id=:id"), {"id": campo_id})
    db.commit()
    return {"ok": True}

@app.patch("/api/config/campos/{campo_id}/reactivar")
def reactivar_campo(campo_id: int, db: Session = Depends(database.get_db)):
    row = db.execute(text("SELECT tabla, tipo_campo FROM configuracion_campos WHERE id=:id"),
                     {"id": campo_id}).fetchone()
    if not row: raise HTTPException(404, "Campo no encontrado")
    tabla, tipo_campo = row
    cuenta = db.execute(text(
        "SELECT COUNT(*) FROM configuracion_campos WHERE tabla=:t AND tipo_campo=:tc AND activo=1 AND es_estandar=0"
    ), {"t": tabla, "tc": tipo_campo}).scalar()
    max_col  = int(db.execute(text("SELECT valor FROM configuracion_parametros WHERE clave='max_columnas'")).scalar() or 5)
    max_json_val = int(db.execute(text("SELECT valor FROM configuracion_parametros WHERE clave='max_json'")).scalar() or 10)
    # Al reactivar JSON verificamos que no supere el límite de activos
    if tipo_campo == "json":
        if cuenta >= max_json_val:
            raise HTTPException(400, f"Límite de {max_json_val} campos JSON activos alcanzado")
    # Columna BD archivada ya contaba para el límite — siempre se puede reactivar
    db.execute(text("UPDATE configuracion_campos SET activo=1 WHERE id=:id"), {"id": campo_id})
    db.commit()
    return {"ok": True}

@app.post("/api/config/ventas/{campo_id}")
def toggle_campo_ventas(campo_id: int, db: Session = Depends(database.get_db)):
    row = db.execute(text("SELECT id, activo FROM configuracion_ventas WHERE campo_id=:id"),
                     {"id": campo_id}).fetchone()
    if row:
        db.execute(text("UPDATE configuracion_ventas SET activo=:a WHERE id=:id"),
                   {"a": 0 if row[1] else 1, "id": row[0]})
    else:
        orden = db.execute(text("SELECT COALESCE(MAX(orden),0)+1 FROM configuracion_ventas")).scalar()
        db.execute(text("INSERT INTO configuracion_ventas (campo_id,activo,orden) VALUES (:c,1,:o)"),
                   {"c": campo_id, "o": orden})
    db.commit()
    return {"ok": True}

# ── API Parámetros de configuración ───────────────────────────────────────────
@app.get("/api/config/parametros")
def get_parametros(db: Session = Depends(database.get_db)):
    rows = db.execute(text("SELECT clave, valor, etiqueta, descripcion FROM configuracion_parametros")).fetchall()
    return [{"clave": r[0], "valor": r[1], "etiqueta": r[2], "descripcion": r[3]} for r in rows]

class ParametroIn(BaseModel):
    valor: str

@app.put("/api/config/parametros/{clave}")
def actualizar_parametro(clave: str, data: ParametroIn, db: Session = Depends(database.get_db)):
    try:
        v = int(data.valor)
        if v < 1: raise ValueError()
    except:
        raise HTTPException(400, "El valor debe ser un número entero mayor que 0")
    db.execute(text("UPDATE configuracion_parametros SET valor=:v WHERE clave=:c"),
               {"v": str(v), "c": clave})
    db.commit()
    return {"ok": True}

# ── API Perfiles de vista ─────────────────────────────────────────────────────
@app.get("/api/perfiles/{pantalla}")
def get_perfiles(pantalla: str, operario_id: int, db: Session = Depends(database.get_db)):
    rows = db.execute(text(
        "SELECT id, nombre, config FROM perfiles_vista WHERE pantalla=:p AND operario_id=:o ORDER BY id"
    ), {"p": pantalla, "o": operario_id}).fetchall()
    return [{"id": r[0], "nombre": r[1], "config": json.loads(r[2] or '{}')} for r in rows]

class PerfilIn(BaseModel):
    pantalla: str
    operario_id: int
    nombre: str
    config: Dict[str, Any] = {}

@app.post("/api/perfiles")
def crear_perfil(data: PerfilIn, db: Session = Depends(database.get_db)):
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    db.execute(text(
        "INSERT INTO perfiles_vista (pantalla, operario_id, nombre, config, creado) VALUES (:p,:o,:n,:c,:f)"
    ), {"p": data.pantalla, "o": data.operario_id, "n": data.nombre,
        "c": json.dumps(data.config, ensure_ascii=False), "f": ahora})
    db.commit()
    row = db.execute(text("SELECT last_insert_rowid()")).scalar()
    return {"ok": True, "id": row}

@app.put("/api/perfiles/{perfil_id}")
def actualizar_perfil(perfil_id: int, data: PerfilIn, db: Session = Depends(database.get_db)):
    db.execute(text("UPDATE perfiles_vista SET nombre=:n, config=:c WHERE id=:id"),
               {"n": data.nombre, "c": json.dumps(data.config, ensure_ascii=False), "id": perfil_id})
    db.commit()
    return {"ok": True}

@app.delete("/api/perfiles/{perfil_id}")
def borrar_perfil(perfil_id: int, db: Session = Depends(database.get_db)):
    db.execute(text("DELETE FROM perfiles_vista WHERE id=:id"), {"id": perfil_id})
    db.commit()
    return {"ok": True}

# ── API Eliminar campo definitivamente (solo Columna BD) ──────────────────────
@app.delete("/api/config/campos/{campo_id}")
def eliminar_campo(campo_id: int, db: Session = Depends(database.get_db)):
    row = db.execute(text(
        "SELECT tabla, nombre, tipo_campo, es_estandar FROM configuracion_campos WHERE id=:id"
    ), {"id": campo_id}).fetchone()
    if not row: raise HTTPException(404, "Campo no encontrado")
    tabla, nombre, tipo_campo, es_estandar = row
    if es_estandar: raise HTTPException(400, "Los campos estándar no se pueden eliminar")
    if tipo_campo != "columna": raise HTTPException(400, "Solo se pueden eliminar definitivamente campos de tipo Columna BD")
    db.execute(text("DELETE FROM configuracion_ventas WHERE campo_id=:id"), {"id": campo_id})
    db.execute(text("DELETE FROM configuracion_campos WHERE id=:id"), {"id": campo_id})
    db.commit()
    return {"ok": True, "nota": f"Columna {nombre} eliminada de configuración. La columna física en BD queda inactiva."}

# ═══════════════════════════════════════════════════════════════════════════════
# NUEVO SISTEMA DINÁMICO — tabla_definiciones como fuente única de verdad
# ═══════════════════════════════════════════════════════════════════════════════

# ── API tabla_definiciones ────────────────────────────────────────────────────
def td_row_to_dict(r):
    cols = ['id','nombre','etiqueta','etiqueta_singular','icono','ruta',
            'padre_tabla','campo_padre_fk','tipo_relacion','campo_principal',
            'campo_secundario','en_nav','orden_nav','en_venta_requerido',
            'en_venta_tipo','en_filtros','es_sistema','activa','extra']
    return dict(zip(cols, r))

@app.get("/api/tablas")
def get_tablas(
    en_nav: Optional[int] = None,
    en_filtros: Optional[int] = None,
    participa_venta: Optional[int] = None,
    db: Session = Depends(database.get_db)
):
    q = "SELECT id,nombre,etiqueta,etiqueta_singular,icono,ruta,padre_tabla,campo_padre_fk," \
        "tipo_relacion,campo_principal,campo_secundario,en_nav,orden_nav,en_venta_requerido," \
        "en_venta_tipo,en_filtros,es_sistema,activa,extra FROM tabla_definiciones WHERE activa=1"
    params = {}
    if en_nav is not None:
        q += " AND en_nav=:en_nav"; params['en_nav'] = en_nav
    if en_filtros is not None:
        q += " AND en_filtros=:en_filtros"; params['en_filtros'] = en_filtros
    if participa_venta is not None:
        q += " AND en_venta_tipo != 'ninguno'";
    q += " ORDER BY orden_nav"
    rows = db.execute(text(q), params).fetchall()
    return [td_row_to_dict(r) for r in rows]

@app.get("/api/tablas/{nombre}/config")
def get_tabla_config(nombre: str, db: Session = Depends(database.get_db)):
    td = db.execute(text(
        "SELECT id,nombre,etiqueta,etiqueta_singular,icono,ruta,padre_tabla,campo_padre_fk,"
        "tipo_relacion,campo_principal,campo_secundario,en_nav,orden_nav,en_venta_requerido,"
        "en_venta_tipo,en_filtros,es_sistema,activa,extra FROM tabla_definiciones WHERE nombre=:n AND activa=1"
    ), {"n": nombre}).fetchone()
    if not td: raise HTTPException(404, "Tabla no definida")
    result = td_row_to_dict(td)

    # Campos: estándar + personalizados activos
    campos = db.execute(text("""
        SELECT id,nombre,etiqueta,tipo,tipo_campo,activo,orden,opciones,es_estandar,
               es_requerido,es_unico,es_bloqueado_venta
        FROM configuracion_campos
        WHERE tabla=:t AND activo=1
        ORDER BY orden
    """), {"t": nombre}).fetchall()
    result['campos'] = [{
        "id": r[0], "nombre": r[1], "etiqueta": r[2], "tipo": r[3],
        "tipo_campo": r[4], "activo": bool(r[5]), "orden": r[6],
        "opciones": r[7] or "", "es_estandar": bool(r[8]),
        "es_requerido": bool(r[9]), "es_unico": bool(r[10]),
        "es_bloqueado_venta": bool(r[11])
    } for r in campos]

    # Si tiene padre, devolver opciones del padre para el selector
    if result.get('padre_tabla'):
        padre = result['padre_tabla']
        td_padre = db.execute(text(
            "SELECT campo_principal FROM tabla_definiciones WHERE nombre=:n"
        ), {"n": padre}).fetchone()
        campo_p = td_padre[0] if td_padre else 'nombre'
        padre_rows = db.execute(text(f"SELECT id, {campo_p} FROM {padre} ORDER BY {campo_p}")).fetchall()
        result['padre_opciones'] = [{"id": r[0], "label": r[1]} for r in padre_rows]

    return result

# ── API consultas_config ──────────────────────────────────────────────────────
@app.get("/api/consultas/config")
def get_consultas_config(db: Session = Depends(database.get_db)):
    rows = db.execute(text("""
        SELECT id,campo,etiqueta,tabla_origen,ancho_default,en_default,orden,tipo_render,es_sistema,activa
        FROM consultas_config WHERE activa=1 ORDER BY orden
    """)).fetchall()
    return [{
        "id": r[0], "campo": r[1], "etiqueta": r[2], "tabla_origen": r[3],
        "ancho_default": r[4], "en_default": bool(r[5]), "orden": r[6],
        "tipo_render": r[7] or "", "es_sistema": bool(r[8]), "activa": bool(r[9])
    } for r in rows]

@app.patch("/api/consultas/config/{col_id}")
async def patch_consultas_config(col_id: int, request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    allowed = {'etiqueta', 'ancho_default', 'en_default', 'orden', 'activa'}
    sets = {k: v for k, v in data.items() if k in allowed}
    if not sets: raise HTTPException(400, "Nada que actualizar")
    sql = "UPDATE consultas_config SET " + ", ".join(f"{k}=:{k}" for k in sets) + " WHERE id=:id"
    db.execute(text(sql), {**sets, "id": col_id})
    db.commit()
    return {"ok": True}

# ── API CRUD genérico /api/entidad/{tabla} ────────────────────────────────────
TABLA_SLUG_RE = re.compile(r'^[a-z][a-z0-9_]*$')

def _check_tabla(nombre: str, db: Session):
    if not TABLA_SLUG_RE.match(nombre):
        raise HTTPException(400, "Nombre de tabla inválido")
    td = db.execute(text(
        "SELECT nombre,campo_principal,campo_secundario,campo_padre_fk FROM tabla_definiciones WHERE nombre=:n AND activa=1"
    ), {"n": nombre}).fetchone()
    if not td: raise HTTPException(404, f"Tabla '{nombre}' no definida en el sistema")
    return td

def _entidad_cols(db: Session, tabla: str):
    return [r[1] for r in db.execute(text(f"PRAGMA table_info({tabla})"))]

def _row_to_dict(row, cols, campos_extra):
    d = dict(zip(cols, row))
    extra_data = parse_extra(d.get('extra', '{}'))
    for c in campos_extra:
        if c['tipo_campo'] == 'columna':
            d.setdefault(c['nombre'], '')
        else:
            d[c['nombre']] = extra_data.get(c['nombre'], '')
    return d

@app.get("/api/entidad/{tabla}")
def listar_entidad(tabla: str, padre_id: Optional[int] = None, db: Session = Depends(database.get_db)):
    td = _check_tabla(tabla, db)
    campo_padre_fk = td[3]
    cols = _entidad_cols(db, tabla)
    campos_extra = campos_extra_tabla(db, tabla)
    q = f"SELECT * FROM {tabla}"
    params = {}
    if padre_id and campo_padre_fk:
        q += f" WHERE {campo_padre_fk}=:padre_id"
        params['padre_id'] = padre_id
    campo_ord = td[1] or 'id'  # campo_principal
    if campo_ord in cols:
        q += f" ORDER BY {campo_ord}"
    rows = db.execute(text(q), params).fetchall()
    return [_row_to_dict(r, cols, campos_extra) for r in rows]

@app.get("/api/entidad/{tabla}/{eid}")
def obtener_entidad(tabla: str, eid: int, db: Session = Depends(database.get_db)):
    _check_tabla(tabla, db)
    cols = _entidad_cols(db, tabla)
    campos_extra = campos_extra_tabla(db, tabla)
    row = db.execute(text(f"SELECT * FROM {tabla} WHERE id=:id"), {"id": eid}).fetchone()
    if not row: raise HTTPException(404, "Registro no encontrado")
    return _row_to_dict(row, cols, campos_extra)

@app.post("/api/entidad/{tabla}")
async def crear_entidad(tabla: str, request: Request, db: Session = Depends(database.get_db)):
    _check_tabla(tabla, db)
    data = await request.json()
    cols = _entidad_cols(db, tabla)
    std_cols = [c for c in cols if c not in ('id', 'extra')]
    campos_extra_def = campos_extra_tabla(db, tabla)
    extra_nombres = {c['nombre'] for c in campos_extra_def if c['tipo_campo'] != 'columna'}

    insert_data = {}
    extra_data = {}
    for k, v in data.items():
        if k == 'id': continue
        if k in std_cols:
            insert_data[k] = v
        elif k not in ('extra',):
            extra_data[k] = v

    if not insert_data: raise HTTPException(400, "Sin datos para insertar")
    fields = list(insert_data.keys())
    sql = f"INSERT INTO {tabla} ({', '.join(fields)}) VALUES ({', '.join(':'+f for f in fields)})"
    db.execute(text(sql), insert_data)
    db.commit()
    new_id = db.execute(text("SELECT last_insert_rowid()")).scalar()
    if extra_data:
        campos_def = campos_extra_tabla(db, tabla)
        guardar_extra(db, tabla, new_id, extra_data, campos_def)
        db.commit()
    return {"ok": True, "id": new_id}

@app.put("/api/entidad/{tabla}/{eid}")
async def actualizar_entidad(tabla: str, eid: int, request: Request, db: Session = Depends(database.get_db)):
    _check_tabla(tabla, db)
    row = db.execute(text(f"SELECT id FROM {tabla} WHERE id=:id"), {"id": eid}).fetchone()
    if not row: raise HTTPException(404, "Registro no encontrado")
    data = await request.json()
    cols = _entidad_cols(db, tabla)
    std_cols = [c for c in cols if c not in ('id', 'extra')]
    campos_extra_def = campos_extra_tabla(db, tabla)

    update_data = {}
    extra_data = {}
    for k, v in data.items():
        if k == 'id': continue
        if k in std_cols:
            update_data[k] = v
        elif k not in ('extra',):
            extra_data[k] = v

    if update_data:
        sets = ", ".join(f"{k}=:{k}" for k in update_data)
        db.execute(text(f"UPDATE {tabla} SET {sets} WHERE id=:id"), {**update_data, "id": eid})
    if extra_data:
        guardar_extra(db, tabla, eid, extra_data, campos_extra_def)
    db.commit()
    return {"ok": True}

@app.delete("/api/entidad/{tabla}/{eid}")
def borrar_entidad(tabla: str, eid: int, db: Session = Depends(database.get_db)):
    _check_tabla(tabla, db)
    row = db.execute(text(f"SELECT id FROM {tabla} WHERE id=:id"), {"id": eid}).fetchone()
    if not row: raise HTTPException(404, "Registro no encontrado")
    db.execute(text(f"DELETE FROM {tabla} WHERE id=:id"), {"id": eid})
    db.commit()
    return {"ok": True}

# ── Página genérica de catálogo ───────────────────────────────────────────────
@app.get("/catalogo/{tabla}")
def catalogo_page(tabla: str):
    return FileResponse("static/pc/catalogo.html")
