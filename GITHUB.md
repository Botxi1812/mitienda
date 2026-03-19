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
- Subir a GitHub **no despliega** en Railway — Railway se actualiza solo al hacer push
