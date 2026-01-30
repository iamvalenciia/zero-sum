# Check Status - Zero Sum Project Status

Este skill verifica el estado actual del proyecto y sistema.

## Uso

Ejecuta estas herramientas en orden:

### 1. Estado General del Proyecto
```
get_status()
```

Muestra:
- Proyecto activo (si hay)
- Fase actual (idle, script, audio, render, complete)
- Archivos existentes
- Proximos pasos sugeridos

### 2. Verificar Imagenes de Personajes
```
validate_render(script_id="[ID]")
```

Valida:
- Imagenes de Analyst existen (close_view, front_view, pov_view)
- Imagenes de Skeptic existen (close_view, front_view, side_view)
- Formato correcto (.jpeg)
- Assets visuales disponibles

### 3. Listar Proyectos
```
list_projects()
```

### 4. Ver Proyectos Archivados
```
list_archived()
```

### 5. Estado de Render en Progreso
```
check_render_status(script_id="[ID]")
get_render_log(tail_lines=100)
```

## Estructura de Archivos Esperada

```
data/
  images/
    analyst/
      close_view/
        CloseMouth_Closed.jpeg
        CloseMouth_Open.jpeg
      front_view/
        FrontMouth_Closed.jpeg
        FrontMouth_Open.jpeg
      pov_view/
        PovMouth_Closed.jpeg
        PovMouth_Open.jpeg
    skeptic/
      close_view/
        CloseMouth_Closed.jpeg
        CloseMouth_Open.jpeg
      front_view/
        FrontMouth_Close.jpeg
        FrontMouth_Open.jpeg
      side_view/
        SideMouth_Closed.jpeg
        SideMouth_Open.jpeg
    images_catalog.json
  shorts/
    scripts/
    audio/
    output/
    images/
```
