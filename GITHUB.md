# Cómo guardar cambios en GitHub

## Repositorio
https://github.com/Botxi1812/mitienda

---

## Guardar cambios (hacer copia)

Cada vez que termines de programar, ejecuta estos 3 comandos en la terminal:

```bash
cd c:/mitienda
git add .
git commit -m "descripción de lo que cambiaste"
git push
```

### Ejemplos de mensajes de commit
```bash
git commit -m "añadí filtro de fechas en ventas"
git commit -m "corregí error en login"
git commit -m "nuevo campo precio en artículos"
```

---

## Desde VSCode (sin escribir comandos)

1. Pulsa `Ctrl+Shift+G` — panel Source Control
2. Verás los archivos modificados en la lista
3. Escribe un mensaje en el campo de texto arriba
4. Pulsa el botón **Commit**
5. Pulsa el botón **Sync** (o el icono de nube) para subir a GitHub

---

## Ver el historial de cambios

```bash
git log --oneline
```

---

## Notas
- El archivo `tienda.db` (base de datos) **no se sube** — está en el .gitignore
- El entorno virtual `venv/` tampoco se sube
- Subir a GitHub **sí actualiza Railway automáticamente** — en 1-2 minutos la URL pública tiene el nuevo código

---

## Trabajar con ramas (para cuando haya usuarios reales)

### Por qué hace falta esto

Cuando el proyecto lo use gente real, no puedes subir código a medias o con errores —
Railway lo desplegaría y los usuarios verían algo roto.

La solución es tener **dos versiones del proyecto en paralelo**:

- **`main`** — la versión estable que ve Railway y los usuarios
- **`desarrollo`** — donde tú pruebas sin miedo a romper nada

### Cómo empezar a trabajar en modo desarrollo

Esto se hace UNA VEZ para crear la rama de desarrollo:

```bash
cd c:/mitienda
git checkout -b desarrollo
```

A partir de ahí estás en la rama `desarrollo`. Puedes modificar, probar, romper cosas —
Railway no se entera porque solo mira `main`.

### El día a día cuando hay ramas

**Mientras programas y pruebas** (en rama desarrollo):
```bash
cd c:/mitienda
git add .
git commit -m "lo que cambiaste"
git push origin desarrollo
```

Esto guarda en GitHub pero NO toca Railway. Puedes hacerlo tantas veces como quieras.

**Cuando algo funciona bien y quieres publicarlo** (pasarlo a main):
```bash
git checkout main          # cambias a la rama principal
git merge desarrollo       # copias los cambios de desarrollo a main
git push                   # subes a GitHub → Railway se actualiza solo
git checkout desarrollo    # vuelves a desarrollo para seguir trabajando
```

### Cómo saber en qué rama estás

```bash
git branch
```

La rama activa aparece con un asterisco `*` delante.

### Resumen visual

```
[desarrollo]  pruebas, cambios, errores...  →  git push origin desarrollo  →  solo GitHub
[main]        versión que funciona          →  git push                    →  GitHub + Railway
```

### IMPORTANTE
- No mezcles: cuando estés en `desarrollo` no hagas `git push` a secas sin más,
  usa siempre `git push origin desarrollo`
- Si te lías con en qué rama estás, ejecuta `git branch` para comprobarlo
- Para volver a `main` en cualquier momento: `git checkout main`
