from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import models, database, json, subprocess, sys

models.Base.metadata.drop_all(bind=database.engine)
models.Base.metadata.create_all(bind=database.engine)
subprocess.run([sys.executable, "seed.py"], check=False)

app = FastAPI(title="Mi Tienda")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Paginas fijas ─────────────────────────────────────────────────────────────
@app.get("/")
def root():           return FileResponse("static/pc/login.html")
@app.get("/ventas")
def ventas():         return FileResponse("static/pc/consultas.html")
@app.get("/nueva-venta")
def nueva_venta():    return FileResponse("static/pc/ventas.html")
@app.get("/configuracion")
def configuracion():  return FileResponse("static/pc/configuracion.html")
@app.get("/movil")
def movil():          return FileResponse("static/movil/login.html")
@app.get("/estructura")
def estructura():     return FileResponse("static/pc/estructura.html")

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

def entidad_a_dict(e):
    d = parse_datos(e.datos)
    result = {"id": e.id, "nombre": e.nombre}
    result.update(d)
    return result

# ── Login: operarios ──────────────────────────────────────────────────────────
@app.get("/api/operarios")
def get_operarios(db: Session = Depends(get_db)):
    # Buscar la tabla marcada como es_login=1; si no existe, devolver vacio
    t = db.query(models.TablaDefinicion).filter_by(es_login=1, activa=1).first()
    if not t:
        return []
    ops = db.query(models.Entidad).filter_by(tabla=t.nombre).order_by(models.Entidad.nombre).all()
    campo_sec = t.campo_secundario or "numero"
    result = []
    for op in ops:
        d = parse_datos(op.datos)
        result.append({
            "id": op.id, "nombre": op.nombre,
            "numero": d.get(campo_sec, d.get("numero", "")),
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
        "es_sistema": t.es_sistema or 0, "es_login": t.es_login or 0, "activa": t.activa,
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

class TablaIn(BaseModel):
    nombre:           str
    etiqueta:         str
    etiqueta_singular: str = ""
    icono:            str = ""
    padre_tabla:      str = ""
    en_nav:           int = 1
    orden_nav:        int = 99
    en_venta_tipo:    str = "ninguno"
    en_filtros:       int = 0

@app.post("/api/tablas")
def crear_tabla(body: TablaIn, db: Session = Depends(get_db)):
    import re, unicodedata
    nombre = unicodedata.normalize("NFKD", body.nombre.lower())
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = re.sub(r"[^a-z0-9]+", "_", nombre).strip("_")
    existe = db.query(models.TablaDefinicion).filter_by(nombre=nombre).first()
    if existe:
        raise HTTPException(400, f"Ya existe una tabla con nombre '{nombre}'")
    ruta = nombre.replace("_", "-")
    etiqueta_singular = body.etiqueta_singular or body.etiqueta.rstrip("s")
    t = models.TablaDefinicion(
        nombre=nombre, etiqueta=body.etiqueta, etiqueta_singular=etiqueta_singular,
        icono=body.icono, ruta=ruta, padre_tabla=body.padre_tabla,
        campo_principal="nombre", en_nav=body.en_nav, orden_nav=body.orden_nav,
        en_venta_tipo=body.en_venta_tipo, en_filtros=body.en_filtros,
        es_sistema=0, es_login=0, activa=1,
    )
    db.add(t)
    # Campo principal 'nombre' siempre
    db.add(models.CampoDefinicion(tabla=nombre, nombre="nombre", etiqueta="Nombre",
        tipo="texto", es_principal=1, es_requerido=1, orden=0, activo=1))
    try:
        db.commit(); db.refresh(t)
    except Exception as e:
        db.rollback(); raise HTTPException(400, str(e))
    return _tabla_dict(t)

@app.delete("/api/tablas/{nombre}")
def eliminar_tabla(nombre: str, db: Session = Depends(get_db)):
    t = db.query(models.TablaDefinicion).filter_by(nombre=nombre).first()
    if not t:
        raise HTTPException(404, f"Tabla '{nombre}' no encontrada")
    # No eliminar tablas con rol fijo
    if t.es_login or t.en_venta_tipo in ("selector", "lineas") or t.es_sistema:
        raise HTTPException(400, "No se puede eliminar una tabla con rol del sistema")
    # Borrar entidades y campos
    db.query(models.Entidad).filter_by(tabla=nombre).delete()
    db.query(models.CampoDefinicion).filter_by(tabla=nombre).delete()
    db.delete(t)
    try:
        db.commit()
    except Exception as e:
        db.rollback(); raise HTTPException(400, str(e))
    return {"ok": True}

@app.get("/api/tablas/{tabla}/config")
def get_tabla_config(tabla: str, db: Session = Depends(get_db)):
    t = db.query(models.TablaDefinicion).filter_by(nombre=tabla).first()
    if not t:
        raise HTTPException(404, f"Tabla '{tabla}' no encontrada")
    campos = db.query(models.CampoDefinicion).filter_by(tabla=tabla, activo=1).order_by(models.CampoDefinicion.orden).all()
    padre_opciones = []
    if t.padre_tabla:
        filas = db.query(models.Entidad).filter_by(tabla=t.padre_tabla).order_by(models.Entidad.nombre).all()
        padre_opciones = [{"id": f.id, "label": f.nombre} for f in filas]
    return {**_tabla_dict(t), "campos": [_campo_dict(c) for c in campos], "padre_opciones": padre_opciones}

# ── Entidades genericas (todas las tablas de catalogo) ────────────────────────
@app.get("/api/entidad/{tabla}")
def get_entidad(tabla: str, db: Session = Depends(get_db)):
    t = db.query(models.TablaDefinicion).filter_by(nombre=tabla).first()
    if not t:
        raise HTTPException(404, f"Tabla '{tabla}' no encontrada")
    filas = db.query(models.Entidad).filter_by(tabla=tabla).order_by(models.Entidad.nombre).all()
    return [entidad_a_dict(f) for f in filas]

@app.post("/api/entidad/{tabla}")
def crear_entidad(tabla: str, body: Dict[str, Any], db: Session = Depends(get_db)):
    t = db.query(models.TablaDefinicion).filter_by(nombre=tabla).first()
    if not t:
        raise HTTPException(404, f"Tabla '{tabla}' no encontrada")
    nombre = body.get("nombre", "").strip()
    if not nombre:
        raise HTTPException(400, "El campo nombre es obligatorio")
    datos_json = {k: v for k, v in body.items() if k not in ("nombre", "id")}
    fila = models.Entidad(tabla=tabla, nombre=nombre, datos=dump_datos(datos_json))
    db.add(fila)
    try:
        db.commit(); db.refresh(fila)
    except Exception as e:
        db.rollback(); raise HTTPException(400, str(e))
    return entidad_a_dict(fila)

@app.put("/api/entidad/{tabla}/{id}")
def actualizar_entidad(tabla: str, id: int, body: Dict[str, Any], db: Session = Depends(get_db)):
    fila = db.query(models.Entidad).filter_by(tabla=tabla, id=id).first()
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
    return entidad_a_dict(fila)

@app.delete("/api/entidad/{tabla}/{id}")
def eliminar_entidad(tabla: str, id: int, db: Session = Depends(get_db)):
    fila = db.query(models.Entidad).filter_by(tabla=tabla, id=id).first()
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
    # Buscar tablas por rol, no por nombre
    t_login    = db.query(models.TablaDefinicion).filter_by(es_login=1,        activa=1).first()
    t_selector = db.query(models.TablaDefinicion).filter_by(en_venta_tipo="selector", activa=1).first()
    t_lineas   = db.query(models.TablaDefinicion).filter_by(en_venta_tipo="lineas",   activa=1).first()
    tabla_op  = t_login.nombre    if t_login    else None
    tabla_cli = t_selector.nombre if t_selector else None
    tabla_art = t_lineas.nombre   if t_lineas   else None
    if not tabla_op or not tabla_art:
        raise HTTPException(500, "Configuracion de ventas incompleta: falta tabla de login o de lineas")
    op = db.query(models.Entidad).filter_by(tabla=tabla_op, id=body.operario_id).first()
    if not op:
        raise HTTPException(404, "Operario no encontrado")
    op_datos = parse_datos(op.datos)
    cli = db.query(models.Entidad).filter_by(tabla=tabla_cli, id=body.cliente_id).first() if (body.cliente_id and tabla_cli) else None
    cli_datos = parse_datos(cli.datos) if cli else {}
    ultimo = db.query(models.LineaVenta).order_by(models.LineaVenta.id.desc()).first()
    if ultimo and ultimo.numero_venta and ultimo.numero_venta.startswith("TCK-"):
        try: num = int(ultimo.numero_venta[4:]) + 1
        except: num = 1
    else:
        num = 1
    numero = f"TCK-{num:05d}"
    ahora = datetime.now()
    for l in body.lineas:
        art = db.query(models.Entidad).filter_by(tabla=tabla_art, id=l.articulo_id).first()
        if not art:
            raise HTTPException(404, f"Articulo {l.articulo_id} no encontrado")
        art_datos = parse_datos(art.datos)
        # Snapshot: todos los campos extra de los tres actores en datos JSON
        snapshot = {}
        for k, v in op_datos.items():
            snapshot[f"op_{k}"] = v
        for k, v in cli_datos.items():
            snapshot[f"cli_{k}"] = v
        for k, v in art_datos.items():
            snapshot[f"art_{k}"] = v
        db.add(models.LineaVenta(
            numero_venta=numero,
            fecha=ahora,
            operario=op.nombre,
            cliente=cli.nombre if cli else "",
            articulo=art.nombre,
            precio_unitario=l.precio_unitario,
            cantidad=l.cantidad,
            importe=round(l.cantidad * l.precio_unitario, 2),
            tipo_pago=l.tipo_pago or "",
            datos=dump_datos(snapshot),
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
        "cliente": l.cliente,
        "articulo": l.articulo,
        "cantidad": l.cantidad,
        "precio_unitario": l.precio_unitario,
        "importe": l.importe,
        "tipo_pago": l.tipo_pago,
        "modificado_por": l.modificado_por,
        "fecha_modificacion": l.fecha_modificacion,
    }
    # Todo el snapshot extra (op_*, cli_*, art_*) se añade tal cual
    d.update(extra)
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
        if c.cantidad is not None:        l.cantidad        = c.cantidad
        if c.precio_unitario is not None: l.precio_unitario = c.precio_unitario
        if c.tipo_pago is not None:       l.tipo_pago       = c.tipo_pago
        if c.modificado_por:              l.modificado_por  = c.modificado_por
        l.importe            = round((l.cantidad or 0) * (l.precio_unitario or 0), 2)
        l.fecha_modificacion = datetime.now().strftime("%d/%m/%Y %H:%M")
    db.commit()
    return {"ok": True}

@app.delete("/api/lineas/{id}")
def delete_linea(id: int, db: Session = Depends(get_db)):
    l = db.query(models.LineaVenta).filter_by(id=id).first()
    if not l: raise HTTPException(404)
    db.delete(l); db.commit()
    return {"ok": True}

# ── Configuracion de campos ───────────────────────────────────────────────────
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

# ── Parametros ────────────────────────────────────────────────────────────────
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
    p = models.PerfilVista(pantalla=body.pantalla, operario_id=body.operario_id, nombre=body.nombre,
        config=dump_datos(body.config), creado=datetime.now().strftime("%Y-%m-%d %H:%M"))
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
        {"campo": "numero_venta",    "etiqueta": "Ticket",     "ancho_default": 90,  "en_default": True,  "tipo_render": "bold"},
        {"campo": "fecha",           "etiqueta": "Fecha",       "ancho_default": 130, "en_default": True,  "tipo_render": ""},
        {"campo": "operario",        "etiqueta": "Operario",    "ancho_default": 120, "en_default": True,  "tipo_render": ""},
        {"campo": "op_departamento", "etiqueta": "Depto.",      "ancho_default": 100, "en_default": False, "tipo_render": ""},
        {"campo": "cliente",         "etiqueta": "Cliente",     "ancho_default": 150, "en_default": True,  "tipo_render": ""},
        {"campo": "cli_ciudad",      "etiqueta": "Ciudad",      "ancho_default": 110, "en_default": False, "tipo_render": ""},
        {"campo": "art_codigo",      "etiqueta": "Cod. Art.",   "ancho_default": 90,  "en_default": False, "tipo_render": ""},
        {"campo": "articulo",        "etiqueta": "Articulo",    "ancho_default": 180, "en_default": True,  "tipo_render": ""},
        {"campo": "cantidad",        "etiqueta": "Cant.",       "ancho_default": 70,  "en_default": True,  "tipo_render": "cantidad"},
        {"campo": "precio_unitario", "etiqueta": "Precio",      "ancho_default": 90,  "en_default": True,  "tipo_render": "moneda"},
        {"campo": "importe",         "etiqueta": "Importe",     "ancho_default": 100, "en_default": True,  "tipo_render": "importe"},
        {"campo": "tipo_pago",       "etiqueta": "Pago",        "ancho_default": 80,  "en_default": True,  "tipo_render": ""},
        {"campo": "modificado_por",  "etiqueta": "Modif. por",  "ancho_default": 110, "en_default": False, "tipo_render": "subdued"},
    ]

# ── Paginas dinamicas de catalogo — DEBE IR AL FINAL para no capturar rutas API ──
@app.get("/{ruta}")
def catalogo_page(ruta: str):
    db = database.SessionLocal()
    try:
        t = db.query(models.TablaDefinicion).filter_by(ruta=ruta, activa=1).first()
    finally:
        db.close()
    if not t:
        raise HTTPException(404)
    return FileResponse("static/pc/catalogo.html")
