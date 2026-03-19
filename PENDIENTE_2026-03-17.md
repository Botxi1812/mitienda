# PENDIENTE — 2026-03-17

---

## Tipos de pantalla definidos

| Tipo | Ejemplos actuales | Construcción | Genérico? |
|---|---|---|---|
| **Catálogo** | Clientes, Artículos, Trabajadores, Departamentos | `catalogo.js` + wrapper HTML | Sí — funciona hoy |
| **TPV / Venta** | Ventas | `ventas.html` dedicado | No — lógica específica (precios especiales, snapshot, TPV) |
| **Generación** | Pedidos, Planificaciones, Ofertas *(futuros)* | `generacion.js` *(pendiente)* | Sí — motor genérico a construir |
| **Informe de Generación** | Consulta ventas, Informe pedidos *(futuros)* | `informe.js` *(pendiente)* | Sí — 1:1 con su Generación, genérico a construir |
| **Consulta cruzada** | Dashboard, Pedido vs Venta *(futuros)* | Pantalla propia por cada caso | No — siempre custom, aparecerán cuando se necesiten |
| **Configuración** | Configuración | `configuracion.html` dedicado | No — único |

### Notas sobre tipos

- **Generación** es estructuralmente similar a Ventas pero sin lógica de TPV: tabla de líneas que crece, campos que se autocompletan, genera documento numerado.
- **Informe de Generación** es el equivalente de `consultas.html` pero para cada tipo de Generación. Comparten patrón: filtros + tabla histórica con columnas configurables + perfiles de vista.
- **Consulta cruzada**: no intentar hacerla genérica. Cuando aparezca una, se construye puntual. Son pocas pero las más valiosas (ej: artículos pedidos sin venta, comparativa oferta vs venta).
- `consultas_config` actual está preparado para generalizarse añadiendo un campo `generacion_tipo`.

---

## Tareas pendientes

### P1 — Wizard de nueva tabla en configuracion.html
Crear UI para añadir una tabla nueva sin tocar código ni BD directamente.

**Lo que debe hacer:**
- Formulario: nombre, etiqueta, etiqueta singular, icono, tipo_relacion, padre_tabla (opcional), en_venta_tipo, en_filtros
- Backend: `POST /api/tablas` que ejecuta `CREATE TABLE` + INSERT en `tabla_definiciones` + campos estándar mínimos en `configuracion_campos`
- Al guardar: la tabla aparece automáticamente en nav, configuración y ventas

**Lo que debe hacer para eliminar/desactivar:**
- Botón en configuracion.html sobre cada tabla no-sistema
- `PATCH /api/tablas/{nombre}/desactivar` → `activa=0` en `tabla_definiciones`
- Desaparece de nav, ventas, filtros de consultas
- Histórico de ventas intacto (valores grabados como texto en `extra`)

---

### P2 — Prueba en navegador y correcciones visuales
Abrir cada pantalla y verificar:
- [ ] Nav dinámica aparece correctamente en todas las páginas
- [ ] Clientes: lista, búsqueda, crear, editar
- [ ] Artículos: lista, búsqueda, crear, editar
- [ ] Trabajadores: modal muestra selector de departamento
- [ ] Departamentos: lista, crear, editar
- [ ] Ventas: carga tablas dinámicas, selector cliente, líneas artículos, confirmar
- [ ] Consultas: carga columnas desde consultas_config, filtros dinámicos, edición inline
- [ ] Configuración: muestra tablas registradas, árbol de ventas con es_bloqueado_venta

---

### P3 — Ampliar consultas con más opciones dinámicas
- Añadir columnas extra desde `consultas_config` (hoy hay 17 sistema)
- Posibilidad de activar/desactivar columnas desde configuracion.html
- Filtro de artículo en filtros principales (hoy solo en tablas con en_filtros=1)
- Considerar si `en_filtros` en tabla_definiciones es suficiente o necesita más granularidad

---

### P4 — Motor genérico Tipo Generación *(cuando se necesite)*
Cuando aparezca el primer caso concreto (pedidos, planificaciones u ofertas):
- Diseñar `generacion.js` equivalente a `catalogo.js` pero para documentos con líneas
- Añadir `tipo_pantalla = 'generacion'`, `tabla_lineas`, `tabla_cabecera` a `tabla_definiciones`
- Extender `consultas_config` con campo `generacion_tipo` para los informes

---

### P5 — Motor genérico Informe de Generación *(cuando se necesite)*
- `informe.js` equivalente a `consultas.html` pero genérico por tipo de generación
- Comparte patrón: filtros configurables + tabla histórica + perfiles de vista
- Leer columnas desde `consultas_config WHERE generacion_tipo = 'pedidos'`
