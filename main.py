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
    return result

# ── Login ─────────────────────────────────────────────────────────────────────
@app.get("/api/operarios")
def get_operarios(db: Session = Depends(get_db)):
    ops = db.query(models.Operario).order_by(models.Operario.nombre).all()
    result = []
    for op in ops:
        d = parse_datos(op.datos)
        result.append({
            "id": op.id, "nombre": op.nombre,
            "numero": d.get("numero", ""),
            "departamento": d.get("departamento", ""),
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
    datos_json = {k: v for k, v in body.items() if k not in ("nombre", "id")}
    kwargs = {"nombre": nombre, "datos": dump_datos(datos_json)}
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
        if k not in ("id", "nombre"):
            datos_json[k] = v
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

# ── Ventas ────────────────────────────────────────────────────────────────────
class LineaIn(BaseModel):
    articulo_id:     int
    cantidad:        float
    precio_unitario: float
    tipo_pago:       Optional[str] = ""

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
    op_datos = parse_datos(op.datos)
    departamento = op_datos.get("departamento", "")
    cli = db.query(models.Cliente).filter_by(id=body.cliente_id).first() if body.cliente_id else None
    cli_datos = parse_datos(cli.datos) if cli else {}
    ultimo = db.query(models.LineaVenta).order_by(models.LineaVenta.id.desc()).first()
    # Extraer numero de venta del ultimo registro
    if ultimo and ultimo.numero_venta and ultimo.numero_venta.startswith("TCK-"):
        try: num = int(ultimo.numero_venta[4:]) + 1
        except: num = 1
    else:
        num = 1
    numero = f"TCK-{num:05d}"
    ahora = datetime.now()
    for l in body.lineas:
        art = db.query(models.Articulo).filter_by(id=l.articulo_id).first()
        if not art:
            raise HTTPException(404, f"Articulo {l.articulo_id} no encontrado")
        art_datos = parse_datos(art.datos)
        db.add(models.LineaVenta(
            numero_venta=numero,
            fecha=ahora,
            operario=op.nombre,
            departamento=departamento,
            cliente=cli.nombre if cli else "",
            articulo=art.nombre,
            codigo=art_datos.get("codigo", ""),
            categoria=art_datos.get("categoria", ""),
            precio_unitario=l.precio_unitario,
            cantidad=l.cantidad,
            importe=round(l.cantidad * l.precio_unitario, 2),
            tipo_pago=l.tipo_pago or "",
            datos=dump_datos({"cliente_cod": cli_datos.get("codigo", ""), "ciudad": cli_datos.get("ciudad", ""), "operario_num": op_datos.get("numero", "")}),
        ))
    db.commit()
    return {"ok": True, "numero": numero}

def _linea_dict(l):
    extra = parse_datos(l.datos)
    d = {
        "id": l.id,
        "numero_venta": l.numero_venta,
        "fecha": l.fecha.strftime("%d/%m/%Y %H:%M") if l.fecha else "",
        "operario": l.operario,
        "operario_num": extra.get("operario_num", ""),
        "departamento": l.departamento,
        "cliente": l.cliente,
        "cliente_cod": extra.get("cliente_cod", ""),
        "ciudad": extra.get("ciudad", ""),
        "articulo": l.articulo,
        "articulo_cod": l.codigo,
        "categoria": l.categoria,
        "cantidad": l.cantidad,
        "precio_unitario": l.precio_unitario,
        "importe": l.importe,
        "tipo_pago": l.tipo_pago,
        "modificado_por": l.modificado_por,
        "fecha_modificacion": l.fecha_modificacion,
    }
    # campos extra JSON adicionales
    for k, v in extra.items():
        if k not in d:
            d[k] = v
    return d

@app.get("/api/ventas")
def get_ventas(
    fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
    cliente:     Optional[str] = None, operario:    Optional[str] = None,
    articulo:    Optional[str] = None, db: Session = Depends(get_db)
):
    q = db.query(models.LineaVenta)
    if fecha_desde:
        try: q = q.filter(models.LineaVenta.fecha >= datetime.strptime(fecha_desde, "%Y-%m-%d"))
        except: pass
    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            q = q.filter(models.LineaVenta.fecha <= fh)
        except: pass
    if cliente:  q = q.filter(models.LineaVenta.cliente.ilike(f"%{cliente}%"))
    if operario: q = q.filter(models.LineaVenta.operario.ilike(f"%{operario}%"))
    if articulo: q = q.filter(models.LineaVenta.articulo.ilike(f"%{articulo}%"))
    return [_linea_dict(l) for l in q.order_by(models.LineaVenta.fecha.desc()).all()]

@app.get("/api/ventas/buscar_campo")
def buscar_campo(campo: str, valor: str, db: Session = Depends(get_db)):
    lineas = db.query(models.LineaVenta).all()
    return [d for l in lineas for d in [_linea_dict(l)] if str(d.get(campo, "")).lower() == valor.lower()]

class LineaCambio(BaseModel):
    id:              int
    cantidad:        Optional[float] = None
    precio_unitario: Optional[float] = None
    tipo_pago:       Optional[str]   = None
    modificado_por:  Optional[str]   = None

@app.patch("/api/lineas")
def patch_lineas(cambios: List[LineaCambio], db: Session = Depends(get_db)):
    for c in cambios:
        l = db.query(models.LineaVenta).filter_by(id=c.id).first()
        if not l: continue
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
    db.delete(l); db.commit()
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
