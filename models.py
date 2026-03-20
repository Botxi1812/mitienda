from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime


# ── Tablas de configuración del sistema ───────────────────────────────────────

class TablaDefinicion(Base):
    """Define cada tabla catálogo: nombre, etiqueta, comportamiento en ventas/nav."""
    __tablename__ = "tabla_definiciones"
    id                 = Column(Integer, primary_key=True, index=True)
    nombre             = Column(String, unique=True, nullable=False)
    etiqueta           = Column(String, nullable=False)
    etiqueta_singular  = Column(String, nullable=False)
    icono              = Column(String, default="")
    ruta               = Column(String, default="")        # ruta URL (ej: "clientes")
    padre_tabla        = Column(String, default="")        # nombre de la tabla padre
    campo_padre_fk     = Column(String, default="")        # columna FK en esta tabla
    campo_principal    = Column(String, default="nombre")  # campo que actúa como nombre visible
    campo_secundario   = Column(String, default="")        # campo secundario (ej: codigo)
    en_nav             = Column(Integer, default=1)
    orden_nav          = Column(Integer, default=0)
    en_venta_tipo      = Column(String, default="ninguno") # ninguno | selector | lineas
    en_venta_requerido = Column(Integer, default=0)
    en_filtros         = Column(Integer, default=0)
    es_sistema         = Column(Integer, default=0)
    activa             = Column(Integer, default=1)


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
    operario_id = Column(Integer, ForeignKey("operarios.id"), index=True)
    nombre      = Column(String, nullable=False)
    config      = Column(Text, default="{}")
    creado      = Column(String, default="")


class CampoDefinicion(Base):
    """Define los campos JSON de cada tabla catálogo."""
    __tablename__ = "campos_definicion"
    id           = Column(Integer, primary_key=True, index=True)
    tabla        = Column(String, nullable=False)     # nombre de la tabla
    nombre       = Column(String, nullable=False)     # clave en el JSON datos
    etiqueta     = Column(String, nullable=False)     # etiqueta visible
    tipo         = Column(String, default="texto")    # texto | numero | fecha | lista
    opciones     = Column(String, default="")         # para tipo lista: "A,B,C"
    es_principal = Column(Integer, default=0)         # 1 = campo principal (no eliminable)
    es_requerido = Column(Integer, default=0)
    orden        = Column(Integer, default=0)
    activo       = Column(Integer, default=1)


# ── Tablas catálogo (estructura mínima: id + nombre_principal + datos JSON) ───

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
    id              = Column(Integer, primary_key=True, index=True)
    nombre          = Column(String, nullable=False, index=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=True)
    datos           = Column(Text, default="{}")
    departamento    = relationship("Departamento")


# ── Precios especiales ────────────────────────────────────────────────────────

class PrecioEspecial(Base):
    __tablename__ = "precios_especiales"
    id          = Column(Integer, primary_key=True, index=True)
    cliente_id  = Column(Integer, ForeignKey("clientes.id"), index=True)
    articulo_id = Column(Integer, ForeignKey("articulos.id"), index=True)
    precio      = Column(Float)
    cliente     = relationship("Cliente")
    articulo    = relationship("Articulo")


# ── Ventas ────────────────────────────────────────────────────────────────────

class Albaran(Base):
    __tablename__ = "albaranes"
    id          = Column(Integer, primary_key=True, index=True)
    numero      = Column(String, unique=True, index=True)
    fecha       = Column(DateTime, default=datetime.datetime.now, index=True)
    cliente_id  = Column(Integer, ForeignKey("clientes.id"), index=True)
    operario_id = Column(Integer, ForeignKey("operarios.id"), index=True)
    cliente     = relationship("Cliente")
    operario    = relationship("Operario")
    lineas      = relationship("LineaVenta", back_populates="albaran")


class LineaVenta(Base):
    __tablename__ = "lineas_venta"
    id                 = Column(Integer, primary_key=True, index=True)
    albaran_id         = Column(Integer, ForeignKey("albaranes.id"), index=True)
    articulo_id        = Column(Integer, ForeignKey("articulos.id"), index=True)
    cantidad           = Column(Float)
    precio_unitario    = Column(Float)
    importe            = Column(Float)
    es_precio_especial = Column(Integer, default=0)
    departamento       = Column(String, default="")   # snapshot del momento
    tipo_pago          = Column(String, default="")
    modificado_por     = Column(String, default="")
    fecha_modificacion = Column(String, default="")
    datos              = Column(Text, default="{}")   # campos extra JSON
    albaran            = relationship("Albaran", back_populates="lineas")
    articulo           = relationship("Articulo")
