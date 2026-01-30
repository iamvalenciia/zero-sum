# Cleanup Project - Zero Sum Project Cleanup

Este skill limpia el proyecto actual para empezar uno nuevo.

## ADVERTENCIA IMPORTANTE

**NUNCA ELIMINES estos archivos/carpetas:**
- `data/images/analyst/**` - Imagenes del personaje Analyst
- `data/images/skeptic/**` - Imagenes del personaje Skeptic
- `data/images/images_catalog.json` - Catalogo de imagenes
- `data/images/final_screen/**` - Pantalla final
- `data/audio/music/**` - Musica de fondo
- `data/font/**` - Fuentes del sistema

Estos son archivos CRITICOS del sistema que se usan en TODOS los videos.

## Workflow Seguro

### Opcion 1: Archivar Proyecto (Recomendado)
```
archive_project(project_id="[ID]", delete_source=True)
```

Esto mueve los archivos del proyecto a `old-videos/` sin eliminar nada critico.

### Opcion 2: Limpiar Workspace
```
cleanup_workspace(archive_first=True, confirm=True)
```

Esto:
1. Archiva el proyecto actual
2. Limpia `data/shorts/` (scripts, audio, output)
3. NO toca `data/images/analyst`, `data/images/skeptic`, etc.

## Que SI se puede limpiar
- `data/shorts/scripts/` - Scripts generados
- `data/shorts/audio/` - Audio generado
- `data/shorts/output/` - Videos renderizados
- `data/shorts/images/` - Imagenes flotantes del proyecto

## Que NUNCA se debe limpiar
- `data/images/analyst/` - Personaje Analyst
- `data/images/skeptic/` - Personaje Skeptic
- `data/images/images_catalog.json` - Catalogo
- `data/font/` - Fuentes
- `data/audio/music/` - Musica de fondo

## Verificar Estado Despues
```
get_status()
list_archived()
```
