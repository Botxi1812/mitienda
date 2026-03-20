from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime


# ── Tablas de configuracion del sistema ──────────────────────────────────────

class TablaDefinicion(Base):
    __tablename__ = "tabla_definiciones"
    id                 = Column(Integer, primary_key=True, index=True)
    nombre             = Column(String, unique=True, nullable=False)
    etiqueta           = Column(String, nullable=False)
    etiqueta_singular  = Column(String, nullable=False)
    icono              = Column(String, default="")
    ruta               = Column(String, default="")
    padre_tabla        = Column(String, default="")
    campo_padre_fk     = Column(String, default="")
    campo_principal    = Column(String, default="nombre")
    campo_secundario   = Column(String, default="")
    en_nav             = Column(Integer, default=1)
    orden_nav          = Column(Integer, default=0)
    en_venta_tipo      = Column(String, default="ninguno")
    en_venta_requerido = Column(Integer, default=0)
    en_filtros         = Column(Integer, default=0)
    es_sistema         = Column(Integer, default=0)
    activa             = Column(Integer, default=1)


class CampoDefinicion(Base):
    __tablename__ = "campos_definicion"
    id           = Column(Integer, primary_key=True, index=True)
    tabla        = Column(String, nullable=False)
    nombre       = Column(String, nullable=False)
    etiqueta     = Column(String, nullable=False)
    tipo         = Column(String, default="texto")
    opciones     = Column(String, default="")
    es_principal = Column(Integer, default=0)
    es_requerido = Column(Integer, default=0)
    orden        = Column(Integer, default=0)
    activo       = Column(Integer, default=1)


class ConfiguracionParametro(Base):
    __tablename__ = "configuracion_parametros"
    clave       = Column(String, primary_key=True)
    valor       = Column(String, default="")
    etiqueta    = Column(String, default="")
    descripcion = Column(String, default="")


class PerfilVista(Base):
    __tablename__ = "perfiles_vista"
    id          = Column(Integer, primary_key=True, index=True)
    pantalla    = Column(String, nullable=False)
    operario_id = Column(Integer, index=True)
    nombre      = Column(String, nullable=False)
    config      = Column(Text, default="{}")
    creado      = Column(String, default="")


# ── Tablas catalogo (id + nombre + datos JSON) ────────────────────────────────

class Departamento(Base):
    __tablename__ = "departamentos"
    id     = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    datos  = Column(Text, default="{}")


class Cliente(Base):
    __tablename__ = "clientes"
    id     = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    datos  = Column(Text, default="{}")


class Articulo(Base):
    __tablename__ = "articulos"
    id     = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    datos  = Column(Text, default="{}")


class Operario(Base):
    __tablename__ = "operarios"
    id     = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    datos  = Column(Text, default="{}")   # incluye: numero, departamento


# ── Ventas (snapshot completo, sin FKs) ───────────────────────────────────────

class LineaVenta(Base):
    __tablename__ = "lineas_venta"
    id              = Column(Integer, primary_key=True, index=True)
    numero_venta    = Column(String, index=True)        # TCK-00001
    fecha           = Column(DateTime, default=datetime.datetime.now, index=True)
    operario        = Column(String, default="")
    departamento    = Column(String, default="")
    cliente         = Column(String, default="")
    articulo        = Column(String, default="")
    codigo          = Column(String, default="")
    categoria       = Column(String, default="")
    precio_unitario = Column(Float, default=0)
    cantidad        = Column(Float, default=0)
    importe         = Column(Float, default=0)
    tipo_pago       = Column(String, default="")
    modificado_por  = Column(String, default="")
    fecha_modificacion = Column(String, default="")
    datos           = Column(Text, default="{}")        # campos extra JSON
