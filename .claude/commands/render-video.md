# Render Video - Zero Sum LDS Video Renderer

Este skill renderiza un video que ya tiene script y audio generados.

## Pre-requisitos
- Script guardado en `data/shorts/scripts/[ID].json`
- Audio generado en `data/shorts/audio/[ID].mp3`

## Workflow

### Paso 1: Verificar Estado
```
get_status()
```

### Paso 2: Validar Pre-requisitos
**OBLIGATORIO** - Siempre ejecutar antes de renderizar:
```
validate_render(script_id="[ID]")
```

Esto verifica:
- Imagenes de personajes existen (analyst, skeptic)
- Assets visuales disponibles
- Audio y timestamps presentes

### Paso 3: Ejecutar Render
```
execute_render(
    script_id="[ID]",
    hook_text="[TEXTO DEL HOOK]",
    output_filename="[NOMBRE_SALIDA]"
)
```

### Paso 4: Monitorear Progreso (si es necesario)
```
check_render_status(script_id="[ID]")
get_render_log(tail_lines=50)
```

## Errores Comunes

### "Character images not found"
Las imagenes deben estar en formato `.jpeg`:
- `data/images/analyst/close_view/CloseMouth_Closed.jpeg`
- `data/images/analyst/close_view/CloseMouth_Open.jpeg`
- etc.

### "Validation failed"
Ejecuta `validate_render` para ver el detalle de errores.

## Archivos Protegidos (NO MODIFICAR)
- `data/images/analyst/**`
- `data/images/skeptic/**`
- `data/images/images_catalog.json`
