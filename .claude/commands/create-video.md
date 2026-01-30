# Create Video - Zero Sum LDS Video Creator

Este skill crea un video completo desde cero sobre un tema dado.

## Workflow Estandarizado

**IMPORTANTE: NUNCA elimines archivos de `data/images/analyst`, `data/images/skeptic`, ni `images_catalog.json`. Estos son archivos protegidos del sistema.**

### Paso 1: Verificar Estado
Primero usa `get_status` para verificar si hay un proyecto activo o archivos residuales.

### Paso 2: Crear Proyecto
Usa `workflow` con operation="create_project" y el topic proporcionado:
```
workflow(operation="create_project", topic="[TOPIC]", hook_question="[HOOK OPCIONAL]")
```

### Paso 3: Crear Script
Genera el script JSON siguiendo la estructura requerida con:
- metadata (topic, hook_text, duration_target)
- dialogue (array de lineas con character, text, emotion, character_poses, visual_assets)

Luego guarda con `save_script`:
```
save_script(project_id="[ID]", script_json={...})
```

### Paso 4: Generar Audio
```
generate_audio(script_id="[ID]")
```

### Paso 5: Validar Render
**SIEMPRE** ejecuta `validate_render` antes de renderizar:
```
validate_render(script_id="[ID]")
```

### Paso 6: Renderizar Video
```
execute_render(script_id="[ID]", hook_text="[HOOK]", output_filename="[FILENAME]")
```

## Archivos Protegidos (NO ELIMINAR)
- `data/images/analyst/**` - Imagenes del personaje Analyst
- `data/images/skeptic/**` - Imagenes del personaje Skeptic
- `data/images/images_catalog.json` - Catalogo de imagenes
- `data/images/final_screen/**` - Pantalla final
- `data/audio/music/**` - Musica de fondo
- `data/font/**` - Fuentes

## Uso
Proporciona el tema del video cuando ejecutes este comando.
