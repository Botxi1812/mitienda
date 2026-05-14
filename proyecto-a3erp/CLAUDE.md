# Proyecto A3ERP — Complemento Excel + Consultas SQL
**Usuario:** Rafa (Rafael, Mercaserveis Catalunya S.A.)
**ERP:** a3 ERP Wolters Kluwer v15.0.0.0 (A10) — servidor cloud — SQL Server
**Partner a3ERP:** Senyum

---

## Propósito

Rafa da soporte técnico y personalización de a3ERP para varias empresas: **MERCASERVEIS**, **HIELOSTORNE** (HIELOSTORNEYCIA) y **MUTUAPEIXATERS**. Su trabajo abarca:
- Personalización de consultas SQL y rejillas del ERP
- Modificación de modelos de impresión
- Desarrollo VBA/Excel (Complemento_A3.xlam + herramientas Excel ad hoc)
- Configuración del ERP e infraestructura

Claude Code actúa como asistente técnico: genera SQL, mejora módulos VBA, explica la estructura de la BD y ayuda a modificar los modelos de impresión de a3ERP.

---

## Conexión a la base de datos

| Parámetro | Valor |
|---|---|
| IP Servidor | `187.33.156.183` |
| Puerto | `1433` |
| Usuario SQL | `sa` |
| Contraseña | `girasol` |
| BD principal | `MERCASERVEIS` |
| BD Hielos Torné | `HIELOSTORNE` |
| BD sistema a3ERP | `A3ERP$SISTEMA` |
| Otras BDs | `MUTUAPEIXATERS` |

- Autenticación Windows NO funciona desde fuera del dominio — usar siempre usuario/contraseña SQL
- Acceso externo requiere **CloudflareWARP** activo en el PC
- ⚠️ `sa` es administrador total

### Cadena de conexión PowerShell
```powershell
$conn.ConnectionString = "Server=187.33.156.183;Database=MERCASERVEIS;User ID=sa;Password=girasol;Connect Timeout=15"
```

---

## Entorno PC de Rafa

- **Usuario:** `Rafael.MERCASERVEIS` / Dominio: `MERCASERVEIS`
- **Escritorio:** `C:\Users\Rafael.MERCASERVEIS\OneDrive - MERCASERVEIS CATALUNYA S.A\Escritorio`
- ⚠️ `$env:USERPROFILE\Desktop` **no funciona** — escritorio redirigido a OneDrive
- Usar siempre `[Environment]::GetFolderPath("Desktop")` en scripts
- PowerShell en el servidor RDP tiene restricciones de ejecución — requiere `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force`

---

## Filosofía de trabajo con Rafa

1. Hacer preguntas aclaratorias antes de proceder
2. Ir campo a campo para probar antes de cambios grandes
3. **No eliminar código** que no sea fruto de la consulta o solución
4. Avisar si un cambio puede dañar otros scripts
5. Preguntar siempre antes de lanzar código en producción
6. **Cambio mínimo**: solo los fragmentos necesarios; nunca modificar código fuera del alcance actual
7. **Aplicar proactivamente** todas las reglas conocidas de a3ERP sin esperar a que Rafa las recuerde
8. Leer la consulta completa antes de hacer preguntas
9. Workarounds pragmáticos aceptados sobre cambios arquitectónicos cuando son viables
10. **Comunicar en español**; Rafa usa mayúsculas para instrucciones y palabras SQL/nombres de tabla

---

## Convenciones SQL de Rafa

- Campos añadidos por Rafa: al **inicio del SELECT**, antes de los originales de A3
- Delimitados con `-- INICIO RAFA` / `-- FIN RAFA`
- Prefijo **`Ht`** para alias → `HtCodCli`, `Ht2NomCli`, `HtDirEnt`
- ⚠️ Los corchetes tipo `[1CodCli]` **no son aceptados** por el diseñador de a3ERP
- Siempre `WITH(NOLOCK)` en tablas grandes

### Formato de documentación en SQL/MD
```sql
/* Modificado por RAFA 2026-05-08 - acción: detalle */
...código modificado...
/* Fin modificacion RAFA 2026-05-08 */
```
Con líneas en blanco separando del código circundante.

---

## Reglas críticas SQL para a3ERP

### Comentarios SQL — MUY IMPORTANTE
- ⚠️ `--` comentarios → a3ERP los interpreta: los campos afectados se pintan de verde y quedan comentados
- ⚠️ `/* */` también problemático en el editor de a3ERP
- ⚠️ `COUNT(*)` → interpretado como inicio de bloque comentario → usar **`COUNT(1)`**
- **Entregar siempre SQL sin comentarios al editor de a3ERP** — los comentarios solo en la documentación MD

### Rejilla Facturas venta — 4 campos obligatorios
Toda consulta personalizada de la rejilla debe incluirlos o da error `"La sentencia SQL debe devolver los siguientes campos"`:
```sql
CABEFACV.IDFACV, CABEFACV.CONTABLE, CABEFACV.IDLAFESTADOFACTURA, CABEFACV.NOAPLICAMOTIVO
```
⚠️ Sacarlos directamente de `CABEFACV`, **no como NULL** — el validador comprueba el tipo de dato

### Sintaxis FROM según tipo de consulta
- **Solo cabecera:** `FROM CABEFACV WITH(NOLOCK) LEFT OUTER JOIN CLIENTES ...` — OK
- **Con LINEFACT:** usar **sintaxis de coma** en FROM, el JOIN va en WHERE:
```sql
FROM CABEFACV WITH (NOLOCK), LINEFACT WITH (NOLOCK)
WHERE CABEFACV.IDFACV = LINEFACT.IDFACV AND ...
```
- ⚠️ `INNER JOIN` en el FROM con LINEFACT → error `"Objeto Parameter mal definido"`

### Subqueries
- ⚠️ a3ERP rechaza **subqueries correlacionadas** y **subselects en el FROM**
- Si falla una consulta compleja, buscar alternativa con JOIN simple o MIN/MAX proxy

### Campos específicos a tener en cuenta
- `CABEALBV.FORPAG` (no `CODPAG`) para forma de pago en cabecera de albaranes
- `LINEALBA` **no tiene timestamp de creación del sistema** — solo `FECCADUC` y `FECENTREGA`; usar `CABEALBV.FECHA` como base para lógica de fechas
- `LINEFACT` usa `NUMLINFAC` (no `NUMLIN`)
- `CARTERA` — tabla muy grande, nunca JOIN sin filtro previo

### Macros de filtro (case exacto)
| Macro | Case |
|---|---|
| `[DevolverRegistros, SysName, 1 = 1]` | SysName |
| `[CondicionTabla, SysName, 1 = 1]` | SysName |
| `[Filtro, SysName, 1 = 1]` | SysName |
| `[CondicionIdentificadores, SysName, 1 = 1]` | SysName |
| `[CondicionCodigo, SysName, 1 = 1]` | SysName |
| `[CondicionRepresentante, Sysname, 1 = 1]` | **Sysname** |
| `[CondicionFechasDocumento, SysName, 1 = 1]` | SysName |
| `[CondicionNumeroDocumento, Sysname, 1 = 1]` | **Sysname** |
| `[CondicionReferenciaDocumento, Sysname, 1 = 1]` | **Sysname** |
| `[TextoBusqueda, SysName, '']` | SysName |

### Campos obligatorios por rejilla
| Rejilla | Campos |
|---|---|
| CLIENTES | `IDORG`, `CODCLI` |
| PROVEEDORES | `IDORG`, `CODPRO` |
| Facturas venta | `IDFACV`, `CONTABLE`, `IDLAFESTADOFACTURA`, `NOAPLICAMOTIVO` |

---

## Modelos de impresión — Diseñador

- ⚠️ **Nunca escribir directamente en la BD de a3ERP**
- Para añadir campos: **copiar un campo existente** en vez de crear desde cero (hereda el binding al dataset)
- Formato de decimales: propiedad **Máscara** → `###,##0.00` o `##0.00`
- Alias con corchetes (`[1Campo]`) rechazados — usar prefijo `Ht`
- Archivos `.DFM` en `C:\Program Files (x86)\A3\A3Erp\plantillas\Listados\`
- Flujo: duplicar en a3ERP → bajar → editar → subir con mismo nombre. **No renombrar**
- Modelos de impresión de facturas: almacenados en la BD de la empresa (no como .DFM en disco)

---

## Complemento_A3.xlam — VBA

El código actual está en: `complemento/dump_actual.txt`
Generado por el módulo `ExportarModulos` del propio complemento.

### Hojas internas del complemento
| Constante | Nombre hoja |
|---|---|
| `HOJA_CLIENTES` | `Clientes` |
| `HOJA_ARTICULOS` | `Articulos` |
| `HOJA_ALBARANES` | `Albaranes` |
| `HOJA_CARTERA` | `Cartera` |
| `HOJA_PVDSAGE` | `PVD SAGE` |
| `HOJA_FILTRO` | `Filtro` |

### Módulos principales
- `FunCartera` — funciones de celda: `DeudaCliente`, `DeudaPendiente`, `DeudaPendiente2`, `RemesasDesde2`
- `FunAlbaranes` — `BuscarTotalAlbaranes` (patrón diccionario, serie `2026/HT`)
- `FunTablas` — `BuscarEnTablas` / `BuscarEnTablas2` (motor genérico con cache array)
- `ModBoton` — callbacks de botones del ribbon
- `ModComplemento_A3` — callbacks ribbon, v3.9
- `ModCartera` — actualización cartera vía ODBC
- `ModAlbaranes` — actualización albaranes vía ODBC
- `ModFormulario` — variables globales: `gFechaInicioAlb`, `gFechaFinalb`, `gDeudaHastaFecha`, `gRemesasDesde`, `gColumna`, `gAceptado`
- `CargaryGrabarCMS` — importar/exportar hojas CMS
- `ExportarModulos` — genera el dump_actual.txt

### Convenciones VBA
- `GetComplemento()` devuelve el Workbook del complemento — usar siempre esto, no `ThisWorkbook` en funciones de celda
- Acceso a tablas: siempre por el complemento, nunca por el libro activo (excepción: `SumarAlbaranesPendientes`)
- Cache de arrays: invalidado cuando cambia el número de filas (`mCacheFilas`)
- **QueryTable** (no ADODB) para conexiones Excel a SQL Server — coherente con arquitectura existente
- **Power Query** preferido para conexiones live/recurrentes; Excel COM para dumps de una sola vez

### Reglas VBA
- `Dim` siempre fuera de bucles `For`
- Usar `CStr()` para cast explícito al pasar elementos de array Variant a parámetros String
- Usar `RGB()` directo en vez de conversión hex en bucles
- **Máximo 24 `_` de continuación de línea** por sentencia — strings largos construirlos en variable intermedia
- `ISNULL()` en SQL para campos nulos al cargar a Excel
- `NumberFormat` explícito en celdas numéricas: `"#,##0.###"` o `"#,##0.000"`

### Formato de entrega de código VBA
- Archivos `.bas` completos para importación directa cuando los cambios son sustanciales
- Herramientas Excel: base `.xlsx` + módulos `.bas` separados

### Actualizar dump_actual.txt
Cuando Rafa ejecute la macro `ExportarModulos` en Excel, generará un nuevo TXT.
Rafa lo sube sobreescribiendo `complemento/dump_actual.txt`.

---

## Tablas principales A3ERP (referencia rápida)

| Tabla/Vista | Descripción | Notas |
|---|---|---|
| `CLIENTES` | Vista clientes (une `__CLIENTES` + `__ORGANIZACION`) | `CODCLI`, `IDORG`, `NOMCLI`, `NIFCLI` |
| `__CLIENTES` | Tabla base clientes | 167 campos |
| `__ORGANIZACION` | Datos comunes organización | 85 campos |
| `PROVEED` | Vista proveedores | `CODPRO`, `IDORG` |
| `ARTICULO` | Artículos | 191 campos |
| `CABEFACV` | Cabecera facturas venta | 297 campos |
| `LINEFACT` | Líneas facturas | `NUMLINFAC` (no `NUMLIN`), 126 campos |
| `CABEALBV` | Cabecera albaranes venta | `FORPAG` para forma de pago, 213 campos |
| `LINEALBA` | Líneas albaranes | 116 campos; sin timestamp de creación del sistema |
| `CABEPEDV` | Pedidos venta | 207 campos |
| `CABEOFEV` | Ofertas/Presupuestos | `TipoCont`, 209 campos |
| `CARTERA` | Efectos | ⚠️ Muy grande — filtrar siempre |
| `DIRENT` | Direcciones entrega | `DEFECTO='T'` para la principal |
| `FORMAPAG` | Formas de pago | `FORPAG`, `DESCFOR` |
| `DOCUPAGO` | Documentos de pago | `DOCPAG`, `DESCDOC` |
| `REPRESEN` | Representantes | `CODREP`, `NOMREP` |
| `CabeRegu`/`LineRegu` | Regulaciones almacén | `PrcMedio` = coste unitario |

---

## Archivos de conocimiento en este repositorio

| Archivo | Descripción |
|---|---|
| `contexto/tablas_a3.txt` | 474 tablas A3ERP con todos los campos y tipos (10.064 columnas) |
| `contexto/vistas_a3.xml` | 220 vistas SQL completas de A3ERP |
| `contexto/conocimiento_a3erp.md` | SQL verificado: plantillas completas, reglas detalladas, macros |
| `contexto/arbol_servidor.txt` | Árbol de directorios del servidor A3ERP (captura 03/03/2026) |
| `complemento/dump_actual.txt` | Código VBA actual del Complemento_A3.xlam (regenerar con ExportarModulos) |

---

## Estado actual del proyecto (última actualización: 14/05/2026)

- **Explorador de Tablas** (`.xlsm`): herramienta para navegar las 474 tablas A3ERP, ver metadatos de campos y generar hojas QueryTable conectadas. Base `.xlsx` + módulos `.bas` separados. Incluye `ModDescripciones.bas` con `GetDescripcion(sTabla, sCampo)`.
- **Albaranes_HIELOSTORNE_v4.xlsx**: hoja `Filtro` con macro `BuscarAlbaranes()`. Selector de cliente en B11 pendiente de implementar.
- **Migración cloud Wolters Kluwer**: problema de licencia identificado — servidor RDP compartido requiere Microsoft 365 Business Premium (Shared Computer Activation), no Business Standard. Pendiente verificar cobertura SPLA con Wolters Kluwer.
- **Fallo SMTP**: credenciales/red descartadas vía test PowerShell manual; causa aislada en `a3ERPCommonMailFactory.dll`. Informe formal generado para Senyum.

## En el horizonte

- Implementar selector de cliente para panel de filtro de Albaranes (celda B11)
- Configurar Power Query nativo como alternativa a larga plazo a los dumps PowerShell
- Copiar modelo de impresión "FACTURAS HT" a otras empresas vía exportación integrada de a3ERP
- Resolver consulta "primera compra" en a3ERP — subquery correlacionada y subselect en FROM rechazados por el validador; alternativas: proxy `MIN(LINEALBA.IDLIN)` o estructura compatible con el validador
