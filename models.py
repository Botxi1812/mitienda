from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Departamento(Base):
    __tablename__ = "departamentos"
    id     = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True)
    extra  = Column(String, default="{}")

class Cliente(Base):
    __tablename__ = "clientes"
    id       = Column(Integer, primary_key=True, index=True)
    codigo   = Column(String, unique=True, index=True)
    nombre   = Column(String, index=True)
    email    = Column(String, default="")
    telefono = Column(String, default="")
    ciudad   = Column(String, default="")
    extra    = Column(String, default="{}")

class Articulo(Base):
    __tablename__ = "articulos"
    id          = Column(Integer, primary_key=True, index=True)
    codigo      = Column(String, unique=True, index=True)
    descripcion = Column(String)
    categoria   = Column(String)
    precio      = Column(Float)
    extra       = Column(String, default="{}")

class PrecioEspecial(Base):
    __tablename__ = "precios_especiales"
    id          = Column(Integer, primary_key=True, index=True)
    cliente_id  = Column(Integer, ForeignKey("clientes.id"), index=True)
    articulo_id = Column(Integer, ForeignKey("articulos.id"), index=True)
    precio      = Column(Float)
    cliente     = relationship("Cliente")
    articulo    = relationship("Articulo")

class Operario(Base):
    __tablename__ = "operarios"
    id              = Column(Integer, primary_key=True, index=True)
    numero          = Column(String, unique=True)
    nombre          = Column(String)
    telefono        = Column(String, default="")
    departamento_id = Column(Integer, ForeignKey("departamentos.id"))
    departamento    = Column(String, default="")
    extra           = Column(String, default="{}")
    dept            = relationship("Departamento")

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
    departamento       = Column(String, default="")   # copiado en el momento
    tipo_pago          = Column(String, default="")   # contado / credito
    modificado_por     = Column(String, default="")   # operario que saneó
    fecha_modificacion = Column(String, default="")   # cuándo se saneó
    extra              = Column(String, default="{}")  # campos extra JSON
    albaran            = relationship("Albaran", back_populates="lineas")
    articulo           = relationship("Articulo")
