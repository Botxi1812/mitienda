from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import models, database, json, subprocess, sys

models.Base.metadata.create_all(bind=database.engine)
subprocess.run([sys.executable, "seed.py"], check=False)

app = FastAPI(title="Mi Tienda")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Páginas ───────────────────────────────────────────────────────────────────
@app.get("/")
def root():               return FileResponse("static/pc/login.html")
@app.get("/nueva-venta")
def nueva_venta():        return FileResponse("static/pc/ventas.html")
@app.get("/ventas")
def ventas():             return FileResponse("static/pc/consultas.html")
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
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def parse_datos(val):
    if not val: return {}
    try: return json.loads(val)
    except: return {}

def dump_datos(d): return json.dumps(d, ensure_ascii=False)

MODEL_MAP = {
    "clientes":      models.Cliente,
    "articulos":     models.Articulo,
    "operarios":     models.Operario,
    "departamentos": models.Departamento,
}

def row_to_dict(row):
    d = parse_datos(getattr(row, "datos", "{}"))
    result = {"id": row.id, "nombre": row.nombre}
    result.update(d)
    if hasattr(row, "departamento_id"):
        result["departamento_id"] = row.departamento_id
        if row.departamento:
            result["departamento"] = row.departamento.nombre
    return result

# ── Login ─────────────────────────────────────────────────────────────────────
@app.get("/api/operarios")
def get_operarios(db: Session = Depends(get_db)):
    ops = db.query(models.Operario).order_by(models.Operario.nombre).all()
    result = []
    for op in ops:
        d = parse_datos(op.datos)
        dept = op.departamento.nombre if op.departamento else ""
        result.append({
            "id": op.id, "nombre": op.nombre,
            "numero": d.get("numero", ""),
            "departamento": dept, "departamento_id": op.departamento_id,
        })
    return result

# ── Tabla definiciones ────────────────────────────────────────────────────────
def _tabla_dict(t):
    return {
        "id": t.id, "nombre": t.nombre,
        "etiqueta": t.etiqueta, "etiqueta_singular": t.etiqueta_singular,
        "icono": t.icono or "", "ruta": t.ruta or t.nombre,
        "padre_tabla": t.padre_tabla or "", "campo_padre_fk": t.campo_padre_fk or "",
        "campo_principal": t.campo_principal or "nombre",
        "campo_secundario": t.campo_secundario or "",
        "en_nav": t.en_nav, "orden_nav": t.orden_nav,
        "en_venta_tipo": t.en_venta_tipo,
        "en_venta_requerido": t.en_venta_requerido or 0,
        "en_filtros": t.en_filtros or 0,
        "es_sistema": t.es_sistema or 0, "activa": t.activa,
    }

def _campo_dict(c):
    return {
        "id": c.id, "tabla": c.tabla, "nombre": c.nombre,
        "etiqueta": c.etiqueta, "tipo": c.tipo,
        "opciones": c.opciones or "", "es_principal": c.es_principal,
        "es_requerido": c.es_requerido, "orden": c.orden, "activo": c.activo,
    }

@app.get("/api/tablas")
def get_tablas(
    en_nav: Optional[int] = None,
    en_filtros: Optional[int] = None,
    participa_venta: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.TablaDefinicion).filter(models.TablaDefinicion.activa == 1)
    if en_nav is not None:
        q = q.filter(models.TablaDefinicion.en_nav == en_nav)
    if en_filtros is not None:
        q = q.filter(models.TablaDefinicion.en_filtros == en_filtros)
    if participa_venta:
        q = q.filter(models.TablaDefinicion.en_venta_tipo != "ninguno")
    return [_tabla_dict(t) for t in q.order_by(models.TablaDefinicion.orden_nav).all()]

@app.get("/api/tablas/{tabla}/config")
def get_tabla_config(tabla: str, db: Session = Depends(get_db)):
    t = db.query(models.TablaDefinicion).filter_by(nombre=tabla).first()
    if not t:
        raise HTTPException(404, f"Tabla '{tabla}' no encontrada")
    campos = db.query(models.CampoDefinicion).filter_by(tabla=tabla, activo=1).order_by(models.CampoDefinicion.orden).all()
    padre_opciones = []
    if t.padre_tabla:
        Modelo = MODEL_MAP.get(t.padre_tabla)
        if Modelo:
            filas = db.query(Modelo).order_by(Modelo.nombre).all()
            padre_opciones = [{"id": f.id, "label": f.nombre} for f in filas]
    return {**_tabla_dict(t), "campos": [_campo_dict(c) for c in campos], "padre_opciones": padre_opciones}

# ── Entidades genéricas ───────────────────────────────────────────────────────
@app.get("/api/entidad/{tabla}")
def get_entidad(tabla: str, db: Session = Depends(get_db)):
    Modelo = MODEL_MAP.get(tabla)
    if not Modelo:
        raise HTTPException(404, f"Tabla '{tabla}' no encontrada")
    return [row_to_dict(f) for f in db.query(Modelo).order_by(Modelo.nombre).all()]

@app.post("/api/entidad/{tabla}")
def crear_entidad(tabla: str, body: Dict[str, Any], db: Session = Depends(get_db)):
    Modelo = MODEL_MAP.get(tabla)
    if not Modelo:
        raise HTTPException(404)
    nombre = body.get("nombre", "").strip()
    if not nombre:
        raise HTTPException(400, "El campo nombre es obligatorio")
    datos_json = {k: v for k, v in body.items() if k not in ("nombre", "departamento_id", "id")}
    kwargs = {"nombre": nombre, "datos": dump_datos(datos_json)}
    if hasattr(Modelo, "departamento_id") and body.get("departamento_id"):
        kwargs["departamento_id"] = body["departamento_id"]
    fila = Modelo(**kwargs)
    db.add(fila)
    try:
        db.commit(); db.refresh(fila)
    except Exception as e:
        db.rollback(); raise HTTPException(400, str(e))
    return row_to_dict(fila)

@app.put("/api/entidad/{tabla}/{id}")
def actualizar_entidad(tabla: str, id: int, body: Dict[str, Any], db: Session = Depends(get_db)):
    Modelo = MODEL_MAP.get(tabla)
    if not Modelo:
        raise HTTPException(404)
    fila = db.query(Modelo).filter(Modelo.id == id).first()
    if not fila:
        raise HTTPException(404)
    if "nombre" in body and body["nombre"]:
        fila.nombre = body["nombre"].strip()
    datos_json = parse_datos(fila.datos)
    for k, v in body.items():
        if k not in ("id", "nombre", "departamento_id", "departamento"):
            datos_json[k] = v
    if "departamento_id" in body and hasattr(fila, "departamento_id"):
        fila.departamento_id = body["departamento_id"]
    fila.datos = dump_datos(datos_json)
    try:
        db.commit(); db.refresh(fila)
    except Exception as e:
        db.rollback(); raise HTTPException(400, str(e))
    return row_to_dict(fila)

@app.delete("/api/entidad/{tabla}/{id}")
def eliminar_entidad(tabla: str, id: int, db: Session = Depends(get_db)):
    Modelo = MODEL_MAP.get(tabla)
    if not Modelo:
        raise HTTPException(404)
    fila = db.query(Modelo).filter(Modelo.id == id).first()
    if not fila:
        raise HTTPException(404)
    db.delete(fila)
    try:
        db.commit()
    except Exception as e:
        db.rollback(); raise HTTPException(400, str(e))
    return {"ok": True}

# ── Precios especiales ────────────────────────────────────────────────────────
@app.get("/api/precio/{cliente_id}/{articulo_id}")
def get_precio(cliente_id: int, articulo_id: int, db: Session = Depends(get_db)):
    pe = db.query(models.PrecioEspecial).filter_by(cliente_id=cliente_id, articulo_id=articulo_id).first()
    if pe:
        return {"precio": pe.precio, "especial": True}
    art = db.query(models.Articulo).filter_by(id=articulo_id).first()
    if not art:
        raise HTTPException(404)
    d = parse_datos(art.datos)
    return {"precio": d.get("precio", 0), "especial": False}

# ── Ventas ────────────────────────────────────────────────────────────────────
class LineaIn(BaseModel):
    articulo_id:        int
    cantidad:           float
    precio_unitario:    float
    es_precio_especial: Optional[bool] = False
    tipo_pago:          Optional[str] = ""

class VentaIn(BaseModel):
    cliente_id:  Optional[int] = None
    operario_id: int
    lineas:      List[LineaIn]

@app.post("/api/ventas")
def crear_venta(body: VentaIn, db: Session = Depends(get_db)):
    if not body.lineas:
        raise HTTPException(400, "Sin lineas")
    op = db.query(models.Operario).filter_by(id=body.operario_id).first()
    if not op:
        raise HTTPException(404, "Operario no encontrado")
    dept_nombre = op.departamento.nombre if op.departamento else ""
    ultimo = db.query(models.Ticket).order_by(models.Ticket.id.desc()).first()
    num = (ultimo.id + 1) if ultimo else 1
    numero = f"TCK-{num:05d}"
    ticket = models.Ticket(numero=numero, fecha=datetime.now(), cliente_id=body.cliente_id, operario_id=body.operario_id)
    db.add(ticket); db.flush()
    for l in body.lineas:
        db.add(models.LineaVenta(
            ticket_id=ticket.id, articulo_id=l.articulo_id,
            cantidad=l.cantidad, precio_unitario=l.precio_unitario,
            importe=round(l.cantidad * l.precio_unitario, 2),
            es_precio_especial=1 if l.es_precio_especial else 0,
            departamento=dept_nombre, tipo_pago=l.tipo_pago or "", datos=dump_datos({}),
        ))
    db.commit()
    return {"ok": True, "numero": numero, "ticket_id": ticket.id}

def _linea_dict(l):
    alb = l.ticket; cli = alb.cliente; op = alb.operario; art = l.articulo
    op_d  = parse_datos(op.datos)  if op  else {}
    cli_d = parse_datos(cli.datos) if cli else {}
    art_d = parse_datos(art.datos) if art else {}
    extra = parse_datos(l.datos)
    d = {
        "id": l.id, "ticket_id": l.ticket_id, "cliente_id": alb.cliente_id, "articulo_id": l.articulo_id,
        "ticket": alb.numero, "fecha": alb.fecha.strftime("%d/%m/%Y %H:%M") if alb.fecha else "",
        "operario": op.nombre if op else "", "operario_num": op_d.get("numero", ""),
        "departamento": l.departamento or (op.departamento.nombre if op and op.departamento else ""),
        "cliente": cli.nombre if cli else "", "cliente_cod": cli_d.get("codigo", ""),
        "ciudad": cli_d.get("ciudad", ""), "articulo": art.nombre if art else "",
        "articulo_cod": art_d.get("codigo", ""), "cantidad": l.cantidad,
        "precio_unitario": l.precio_unitario, "importe": l.importe,
        "especial": l.es_precio_especial == 1, "tipo_pago": l.tipo_pago or "",
        "modificado_por": l.modificado_por or "", "fecha_modificacion": l.fecha_modificacion or "",
    }
    d.update(extra)
    return d

@app.get("/api/ventas")
def get_ventas(
    fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
    cliente_id: Optional[int] = None, operario_id: Optional[int] = None,
    articulo_id: Optional[int] = None, db: Session = Depends(get_db)
):
    q = db.query(models.LineaVenta).join(models.Ticket)
    if fecha_desde:
        try: q = q.filter(models.Ticket.fecha >= datetime.strptime(fecha_desde, "%Y-%m-%d"))
        except: pass
    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            q = q.filter(models.Ticket.fecha <= fh)
        except: pass
    if cliente_id:  q = q.filter(models.Ticket.cliente_id  == cliente_id)
    if operario_id: q = q.filter(models.Ticket.operario_id == operario_id)
    if articulo_id: q = q.filter(models.LineaVenta.articulo_id == articulo_id)
    return [_linea_dict(l) for l in q.order_by(models.Ticket.fecha.desc()).all()]

@app.get("/api/ventas/buscar_campo")
def buscar_campo(campo: str, valor: str, db: Session = Depends(get_db)):
    lineas = db.query(models.LineaVenta).join(models.Ticket).all()
    return [d for l in lineas for d in [_linea_dict(l)] if str(d.get(campo, "")).lower() == valor.lower()]

class LineaCambio(BaseModel):
    id:              int
    articulo_id:     Optional[int]   = None
    cantidad:        Optional[float] = None
    precio_unitario: Optional[float] = None
    tipo_pago:       Optional[str]   = None
    modificado_por:  Optional[str]   = None

@app.patch("/api/lineas")
def patch_lineas(cambios: List[LineaCambio], db: Session = Depends(get_db)):
    for c in cambios:
        l = db.query(models.LineaVenta).filter_by(id=c.id).first()
        if not l: continue
        if c.articulo_id is not None:     l.articulo_id      = c.articulo_id
        if c.cantidad is not None:        l.cantidad         = c.cantidad
        if c.precio_unitario is not None: l.precio_unitario  = c.precio_unitario
        if c.tipo_pago is not None:       l.tipo_pago        = c.tipo_pago
        if c.modificado_por:              l.modificado_por   = c.modificado_por
        l.importe            = round((l.cantidad or 0) * (l.precio_unitario or 0), 2)
        l.fecha_modificacion = datetime.now().strftime("%d/%m/%Y %H:%M")
    db.commit()
    return {"ok": True}

@app.delete("/api/lineas/{id}")
def delete_linea(id: int, modificado_por: Optional[str] = "", db: Session = Depends(get_db)):
    l = db.query(models.LineaVenta).filter_by(id=id).first()
    if not l: raise HTTPException(404)
    ticket_id = l.ticket_id
    db.delete(l); db.commit()
    if db.query(models.LineaVenta).filter_by(ticket_id=ticket_id).count() == 0:
        t = db.query(models.Ticket).filter_by(id=ticket_id).first()
        if t: db.delete(t); db.commit()
    return {"ok": True}

# ── Configuración de campos ───────────────────────────────────────────────────
@app.get("/api/config/campos")
def get_config_campos(db: Session = Depends(get_db)):
    campos = db.query(models.CampoDefinicion).filter_by(activo=1).order_by(models.CampoDefinicion.orden).all()
    result = {}
    for c in campos:
        result.setdefault(c.tabla, []).append(_campo_dict(c))
    return result

class CampoIn(BaseModel):
    tabla: str; etiqueta: str; tipo: str = "texto"; opciones: str = ""

@app.post("/api/config/campos")
def crear_campo(body: CampoIn, db: Session = Depends(get_db)):
    import re, unicodedata
    nombre = unicodedata.normalize("NFKD", body.etiqueta.lower())
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = re.sub(r"[^a-z0-9]+", "_", nombre).strip("_")
    param = db.query(models.ConfiguracionParametro).filter_by(clave="max_json").first()
    max_json = int(param.valor) if param else 15
    actuales = db.query(models.CampoDefinicion).filter_by(tabla=body.tabla, activo=1, es_principal=0).count()
    if actuales >= max_json:
        raise HTTPException(400, f"Limite de {max_json} campos JSON alcanzado")
    ultimo = db.query(models.CampoDefinicion).filter_by(tabla=body.tabla).order_by(models.CampoDefinicion.orden.desc()).first()
    orden = (ultimo.orden + 1) if ultimo else 1
    c = models.CampoDefinicion(tabla=body.tabla, nombre=nombre, etiqueta=body.etiqueta, tipo=body.tipo, opciones=body.opciones, orden=orden, activo=1)
    db.add(c)
    try:
        db.commit(); db.refresh(c)
    except Exception as e:
        db.rollback(); raise HTTPException(400, str(e))
    return _campo_dict(c)

@app.delete("/api/config/campos/{id}")
def eliminar_campo(id: int, db: Session = Depends(get_db)):
    c = db.query(models.CampoDefinicion).filter_by(id=id).first()
    if not c: raise HTTPException(404)
    if c.es_principal: raise HTTPException(400, "No se puede eliminar el campo principal")
    db.delete(c); db.commit()
    return {"ok": True}

# ── Parámetros ────────────────────────────────────────────────────────────────
@app.get("/api/config/parametros")
def get_parametros(db: Session = Depends(get_db)):
    return [{"clave": p.clave, "valor": p.valor, "etiqueta": p.etiqueta} for p in db.query(models.ConfiguracionParametro).all()]

class ParamIn(BaseModel):
    valor: str

@app.put("/api/config/parametros/{clave}")
def set_parametro(clave: str, body: ParamIn, db: Session = Depends(get_db)):
    p = db.query(models.ConfiguracionParametro).filter_by(clave=clave).first()
    if not p:
        p = models.ConfiguracionParametro(clave=clave, valor=body.valor); db.add(p)
    else:
        p.valor = body.valor
    db.commit()
    return {"ok": True}

# ── Perfiles de vista ─────────────────────────────────────────────────────────
@app.get("/api/perfiles/{pantalla}")
def get_perfiles(pantalla: str, operario_id: int, db: Session = Depends(get_db)):
    ps = db.query(models.PerfilVista).filter_by(pantalla=pantalla, operario_id=operario_id).all()
    return [{"id": p.id, "nombre": p.nombre, "config": parse_datos(p.config)} for p in ps]

class PerfilIn(BaseModel):
    pantalla: str; operario_id: int; nombre: str; config: Dict[str, Any] = {}

@app.post("/api/perfiles")
def crear_perfil(body: PerfilIn, db: Session = Depends(get_db)):
    p = models.PerfilVista(pantalla=body.pantalla, operario_id=body.operario_id, nombre=body.nombre, config=dump_datos(body.config), creado=datetime.now().strftime("%Y-%m-%d %H:%M"))
    db.add(p); db.commit(); db.refresh(p)
    return {"ok": True, "id": p.id}

@app.put("/api/perfiles/{id}")
def actualizar_perfil(id: int, body: PerfilIn, db: Session = Depends(get_db)):
    p = db.query(models.PerfilVista).filter_by(id=id).first()
    if not p: raise HTTPException(404)
    p.nombre = body.nombre; p.config = dump_datos(body.config)
    db.commit()
    return {"ok": True}

@app.delete("/api/perfiles/{id}")
def borrar_perfil(id: int, db: Session = Depends(get_db)):
    p = db.query(models.PerfilVista).filter_by(id=id).first()
    if not p: raise HTTPException(404)
    db.delete(p); db.commit()
    return {"ok": True}

# ── Consultas config ──────────────────────────────────────────────────────────
@app.get("/api/consultas/config")
def get_consultas_config():
    return [
        {"campo": "ticket",         "etiqueta": "Ticket",      "ancho_default": 90,  "en_default": True,  "tipo_render": "bold"},
        {"campo": "fecha",           "etiqueta": "Fecha",        "ancho_default": 130, "en_default": True,  "tipo_render": ""},
        {"campo": "operario",        "etiqueta": "Operario",     "ancho_default": 120, "en_default": True,  "tipo_render": ""},
        {"campo": "departamento",    "etiqueta": "Depto.",       "ancho_default": 100, "en_default": False, "tipo_render": ""},
        {"campo": "cliente",         "etiqueta": "Cliente",      "ancho_default": 150, "en_default": True,  "tipo_render": ""},
        {"campo": "ciudad",          "etiqueta": "Ciudad",       "ancho_default": 110, "en_default": False, "tipo_render": ""},
        {"campo": "articulo_cod",    "etiqueta": "Cod. Art.",    "ancho_default": 90,  "en_default": False, "tipo_render": ""},
        {"campo": "articulo",        "etiqueta": "Articulo",     "ancho_default": 180, "en_default": True,  "tipo_render": ""},
        {"campo": "cantidad",        "etiqueta": "Cant.",        "ancho_default": 70,  "en_default": True,  "tipo_render": "cantidad"},
        {"campo": "precio_unitario", "etiqueta": "Precio",       "ancho_default": 90,  "en_default": True,  "tipo_render": "moneda"},
        {"campo": "importe",         "etiqueta": "Importe",      "ancho_default": 100, "en_default": True,  "tipo_render": "importe"},
        {"campo": "especial",        "etiqueta": "Especial",     "ancho_default": 80,  "en_default": False, "tipo_render": "badge_especial"},
        {"campo": "tipo_pago",       "etiqueta": "Pago",         "ancho_default": 80,  "en_default": True,  "tipo_render": ""},
        {"campo": "modificado_por",  "etiqueta": "Modif. por",   "ancho_default": 110, "en_default": False, "tipo_render": "subdued"},
    ]
