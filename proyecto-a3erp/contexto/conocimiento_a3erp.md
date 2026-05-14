# Conocimiento a3 ERP - Rafa
**Timestamp original:** 2026-03-18 06:56:59
**Última actualización:** 2026-03-18 12:00:00

---

## 1. Entorno y versión

- a3 ERP (Wolters Kluwer) versión **15.0.0.0 (A10)**
- Servidor remoto (cloud Wolters Kluwer) — acceso vía RDP
- SQL Server: usa `WITH(NOLOCK)`, `CAST`, `DECIMAL`
- Diseñador de modelos de impresión integrado en a3ERP

---

## 2. Conexión a la base de datos

| Parámetro | Valor |
|---|---|
| IP Servidor | `187.33.156.183` |
| Puerto | `1433` (accesible desde exterior) |
| Usuario SQL | `sa` |
| Contraseña | `girasol` |
| BD principal | `MERCASERVEIS` |
| BD Hielos Torné | `HIELOSTORNE` |
| BD sistema a3ERP | `A3ERP$SISTEMA` |
| Otras BDs | `MUTUAPEIXATERS` |

- Autenticación Windows **no funciona** desde fuera del dominio
- Acceso externo requiere **CloudflareWARP** activo
- ⚠️ `sa` es administrador total

### Cadena de conexión PowerShell
```powershell
$conn.ConnectionString = "Server=187.33.156.183;Database=MERCASERVEIS;User ID=sa;Password=girasol;Connect Timeout=15"
```

---

## 3. Plantillas SQL verificadas

### Cabecera de facturas (sin líneas)
```sql
SELECT
  CABEFACV.IDFACV, CABEFACV.CONTABLE,
  CABEFACV.IDLAFESTADOFACTURA, CABEFACV.NOAPLICAMOTIVO,
  CABEFACV.SERIE, CABEFACV.NUMDOC AS NUM, CABEFACV.FECHA,
  CABEFACV.REFERENCIA, CABEFACV.CODCLI, CABEFACV.NOMCLI,
  CABEFACV.CODPER AS PERSONA, CABEFACV.CODTRA AS TRANSPORTISTA,
  CABEFACV.CODREP AS REPRESENTANTE, CABEFACV.EMAIL,
  CABEFACV.TOTMONEDA AS TOTALCONIVA,
  CLIENTES.E_MAIL_DOCS AS EMAIL_ENVIO_DOCS,
  CLIENTES.NIFCLI AS NIF_CLIENTE
FROM CABEFACV WITH (NOLOCK)
LEFT OUTER JOIN CLIENTES ON CABEFACV.CODCLI = CLIENTES.CODCLI
WHERE ( [DevolverRegistros, SysName, 1 = 1])
  AND ( [CondicionTabla, SysName, 1 = 1])
  AND ( [Filtro, SysName, 1 = 1])
  AND ( [CondicionIdentificadores, SysName, 1 = 1])
  AND ( [CondicionCodigo, SysName, 1 = 1])
  AND ( [CondicionRepresentante, Sysname, 1 = 1])
  AND ( [CondicionFechasDocumento, SysName, 1 = 1])
  AND ( [CondicionNumeroDocumento, Sysname, 1 = 1])
  AND ( [CondicionReferenciaDocumento, Sysname, 1 = 1])
  AND ( ( '[TextoBusqueda, SysName, '']' = '') OR
        ( CABEFACV.IDFACV   LIKE '%[TextoBusqueda, SysName, '']%') OR
        ( CABEFACV.SERIE    LIKE '%[TextoBusqueda, SysName, '']%') OR
        ( CABEFACV.NUMDOC   LIKE '%[TextoBusqueda, SysName, '']%') OR
        ( CABEFACV.CODCLI   LIKE '%[TextoBusqueda, SysName, '']%') OR
        ( CABEFACV.NOMCLI   LIKE '%[TextoBusqueda, SysName, '']%'))
ORDER BY CABEFACV.TIPOCONT, CABEFACV.SERIE, CABEFACV.NUMDOC,
         CABEFACV.FECHA, CABEFACV.REFERENCIA, CABEFACV.CODCLI, CABEFACV.NOMCLI
```

### Cabecera + líneas de factura
```sql
SELECT
  CABEFACV.IDFACV, CABEFACV.CONTABLE,
  CABEFACV.IDLAFESTADOFACTURA, CABEFACV.NOAPLICAMOTIVO,
  CABEFACV.TIPOCONT, CABEFACV.SERIE, CABEFACV.NUMDOC AS NUM,
  CABEFACV.FECHA, CABEFACV.REFERENCIA, CABEFACV.CODCLI, CABEFACV.NOMCLI,
  CABEFACV.CODPER AS PERSONA, CABEFACV.CODTRA AS TRANSPORTISTA,
  CABEFACV.CODREP AS REPRESENTANTE, CABEFACV.FORPAG AS FP,
  LINEFACT.NUMLINFAC, LINEFACT.CODART, LINEFACT.DESCLIN,
  LINEFACT.UNIDADES, LINEFACT.PRCMONEDA AS PVD,
  LINEFACT.UNIDADES * LINEFACT.PRCMONEDA AS TOTAL,
  LINEFACT.CENTROCOSTE, LINEFACT.CTACONL
FROM CABEFACV WITH (NOLOCK), LINEFACT WITH (NOLOCK)
WHERE ( [DevolverRegistros, SysName, 1 = 1])
AND CABEFACV.IDFACV = LINEFACT.IDFACV
  AND ( [CondicionTabla, SysName, 1 = 1])
  AND ( [Filtro, SysName, 1 = 1])
  AND ( [CondicionIdentificadores, SysName, 1 = 1])
  AND ( [CondicionCodigo, SysName, 1 = 1])
  AND ( [CondicionRepresentante, Sysname, 1 = 1])
  AND ( [CondicionFechasDocumento, SysName, 1 = 1])
  AND ( [CondicionNumeroDocumento, Sysname, 1 = 1])
  AND ( [CondicionReferenciaDocumento, Sysname, 1 = 1])
  AND ( ( '[TextoBusqueda, SysName, '']' = '') OR
        ( CABEFACV.SERIE   LIKE '%[TextoBusqueda, SysName, '']%') OR
        ( CABEFACV.NUMDOC  LIKE '%[TextoBusqueda, SysName, '']%') OR
        ( CABEFACV.CODCLI  LIKE '%[TextoBusqueda, SysName, '']%') OR
        ( CABEFACV.NOMCLI  LIKE '%[TextoBusqueda, SysName, '']%'))
ORDER BY CABEFACV.TIPOCONT, CABEFACV.SERIE, CABEFACV.NUMDOC,
         CABEFACV.REFERENCIA, CABEFACV.CODCLI, CABEFACV.NOMCLI, LINEFACT.NUMLINFAC
```

### Patrón base clientes
```sql
SELECT
    C.IDORG, C.CODCLI,
    C.NOMCLI, C.NIFCLI, C.DIRCLI, C.POBCLI, C.TELCLI, C.E_MAIL,
    D.NOMENT, D.DIRENT1, D.POBENT, D.TELENT1,
    C.FORPAG, FP.DESCFOR AS DESC_FORPAG,
    C.DOCPAG, DP.DESCDOC AS DESC_DOCPAG,
    C.CODREP, R.NOMREP
FROM CLIENTES C WITH (NOLOCK)
LEFT JOIN DIRENT    D  WITH (NOLOCK) ON D.CODCLI  = C.CODCLI AND D.DEFECTO = 'T'
LEFT JOIN FORMAPAG  FP WITH (NOLOCK) ON FP.FORPAG = C.FORPAG
LEFT JOIN DOCUPAGO  DP WITH (NOLOCK) ON DP.DOCPAG = C.DOCPAG
LEFT JOIN REPRESEN  R  WITH (NOLOCK) ON R.CODREP  = C.CODREP
WHERE ( [DevolverRegistros, SysName, 1 = 1])
  AND ( [CondicionTabla,    SysName, 1 = 1])
  AND ( [Filtro,            SysName, 1 = 1])
  AND ( ('[TextoBusqueda, SysName, '']' = '') OR
        ( C.CODCLI LIKE '%[TextoBusqueda, SysName, '']%') OR
        ( C.NOMCLI LIKE '%[TextoBusqueda, SysName, '']%') OR
        ( C.TELCLI LIKE '%[TextoBusqueda, SysName, '']%'))
ORDER BY C.CODCLI
```

---

## 4. Macros de filtro (case exacto)

| Macro | Case correcto |
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

---

## 5. Campos obligatorios por rejilla

| Rejilla | Campos obligatorios |
|---|---|
| CLIENTES | `IDORG`, `CODCLI` |
| PROVEEDORES | `IDORG`, `CODPRO` |
| Facturas venta | `IDFACV`, `CONTABLE`, `IDLAFESTADOFACTURA`, `NOAPLICAMOTIVO` |
