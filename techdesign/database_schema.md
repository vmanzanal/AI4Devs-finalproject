# Esquema de Base de Datos - SEPE Templates Comparator

## Resumen General

El sistema SEPE Templates Comparator utiliza una base de datos relacional diseñada para gestionar usuarios, plantillas PDF del SEPE, versiones de plantillas y comparaciones detalladas entre plantillas. La arquitectura está optimizada para rastrear cambios estructurales en formularios PDF y proporcionar análisis comparativos detallados.

## Modelos de Datos

### 1. Tabla: `users`

**Propósito:** Gestión de usuarios del sistema, incluyendo autenticación y perfiles de usuario para el acceso al comparador de plantillas SEPE.
Analiza la estructura de la base de datos del proyecto leyendo exclusivamente los modelos de SQLAlchemy definidos en la carpeta `app/models/`.

### Requisito

Genera un documento Markdown (`database_schema.md`) con el esquema de la base de datos.

### Formato de Salida

Para cada modelo (tabla), proporciona la siguiente información:

1.  **Nombre de la Tabla** (Ejemplo: `users`).
2.  **Propósito** (Una breve descripción basada en el contexto del proyecto SEPE Comparator).
3.  **Columnas:** Lista el `nombre_de_la_columna`, su `Tipo de Dato SQL` (ej: UUID, VARCHAR), y las propiedades clave (`PK`, `FK`, `Nullable`).
4.  **Relaciones:** Indica las relaciones (Relationships) de SQLAlchemy definidas con otros modelos (Ej: `users` tiene una relación de 1:N con `pdf_templates`).

### Enfoque Específico para Análisis

1.  **Analiza la tabla 'users'**: Verifica su estructura básica.
2.  **Analiza 'pdf_templates' y 'template_versions'**: Describe cómo se maneja el versionado.
3.  **Analiza las tablas 'comparison_fields' y 'comparisons'**: Describe cómo se guarda el resultado de la comparación, que es el núcleo del negocio.

Genera el documento completo basado en el código de los modelos de SQLAlchemy.
**Columnas:**
| Nombre | Tipo SQL | Propiedades | Descripción |
|--------|----------|-------------|-------------|
| `id` | INTEGER | PK, Index | Identificador único del usuario |
| `email` | VARCHAR(255) | Unique, Not Null, Index | Email del usuario (usado para login) |
| `hashed_password` | VARCHAR(255) | Not Null | Contraseña hasheada del usuario |
| `full_name` | VARCHAR(255) | Nullable | Nombre completo del usuario |
| `is_active` | BOOLEAN | Default: True, Index | Estado activo del usuario |
| `is_superuser` | BOOLEAN | Default: False | Permisos de superusuario |
| `created_at` | DATETIME | Server Default: now() | Fecha de creación del usuario |
| `updated_at` | DATETIME | On Update: now() | Fecha de última actualización |

**Relaciones:**

- **1:N con `pdf_templates`**: Un usuario puede subir múltiples plantillas PDF (`uploaded_templates`)
- **1:N con `comparisons`**: Un usuario puede crear múltiples comparaciones (`created_comparisons`)

---

### 2. Tabla: `pdf_templates`

**Propósito:** Almacenamiento de metadatos de plantillas PDF del SEPE, incluyendo información del archivo, versiones y estadísticas básicas de campos.

**Columnas:**
| Nombre | Tipo SQL | Propiedades | Descripción |
|--------|----------|-------------|-------------|
| `id` | INTEGER | PK, Index | Identificador único de la plantilla |
| `name` | VARCHAR(255) | Not Null, Index | Nombre de la plantilla PDF |
| `version` | VARCHAR(50) | Not Null, Index | Versión actual de la plantilla |
| `file_path` | VARCHAR(500) | Not Null | Ruta del archivo PDF en el sistema |
| `file_size_bytes` | INTEGER | Not Null | Tamaño del archivo en bytes |
| `field_count` | INTEGER | Default: 0 | Número de campos detectados en el PDF |
| `sepe_url` | VARCHAR(1000) | Nullable | URL oficial del SEPE donde se encuentra la plantilla |
| `uploaded_by` | INTEGER | FK to users.id, Nullable | Usuario que subió la plantilla |
| `created_at` | DATETIME | Server Default: now(), Index | Fecha de creación |
| `updated_at` | DATETIME | On Update: now() | Fecha de última actualización |

**Relaciones:**

- **N:1 con `users`**: Múltiples plantillas pueden ser subidas por un usuario (`uploader`)
- **1:N con `template_versions`**: Una plantilla puede tener múltiples versiones (`versions`)
- **1:N con `comparisons` (como source)**: Una plantilla puede ser fuente en múltiples comparaciones (`source_comparisons`)
- **1:N con `comparisons` (como target)**: Una plantilla puede ser objetivo en múltiples comparaciones (`target_comparisons`)

---

### 3. Tabla: `template_versions`

**Propósito:** Gestión del historial de versiones de plantillas PDF, permitiendo rastrear cambios y mantener un registro de evolución de las plantillas del SEPE a lo largo del tiempo.

**Columnas:**
| Nombre | Tipo SQL | Propiedades | Descripción |
|--------|----------|-------------|-------------|
| `id` | INTEGER | PK, Index | Identificador único de la versión |
| `template_id` | INTEGER | FK to pdf_templates.id, Not Null, Index | Referencia a la plantilla base |
| `version_number` | VARCHAR(50) | Not Null | Número/código de versión |
| `change_summary` | TEXT | Nullable | Resumen de cambios en esta versión |
| `is_current` | BOOLEAN | Default: False, Index | Indica si es la versión actual |
| `created_at` | DATETIME | Server Default: now() | Fecha de creación de la versión |

**Relaciones:**

- **N:1 con `pdf_templates`**: Múltiples versiones pertenecen a una plantilla (`template`)

**Estrategia de Versionado:**

- Cada plantilla PDF puede tener múltiples versiones históricas
- Solo una versión puede estar marcada como `is_current = True` por plantilla
- El `change_summary` permite documentar qué cambió entre versiones
- Facilita la trazabilidad de evolución de formularios SEPE

---

### 4. Tabla: `comparisons`

**Propósito:** Núcleo del negocio - almacena metadatos de comparaciones entre plantillas PDF del SEPE, incluyendo estado del proceso, estadísticas y referencias a las plantillas comparadas.

**Columnas:**
| Nombre | Tipo SQL | Propiedades | Descripción |
|--------|----------|-------------|-------------|
| `id` | INTEGER | PK, Index | Identificador único de la comparación |
| `source_template_id` | INTEGER | FK to pdf_templates.id, Not Null, Index | Plantilla fuente de la comparación |
| `target_template_id` | INTEGER | FK to pdf_templates.id, Not Null, Index | Plantilla objetivo de la comparación |
| `comparison_type` | VARCHAR(50) | Default: "structure" | Tipo de comparación realizada |
| `status` | VARCHAR(50) | Default: "pending", Index | Estado del proceso de comparación |
| `differences_count` | INTEGER | Default: 0 | Número total de diferencias encontradas |
| `created_by` | INTEGER | FK to users.id, Nullable | Usuario que creó la comparación |
| `created_at` | DATETIME | Server Default: now(), Index | Fecha de inicio de la comparación |
| `completed_at` | DATETIME | Nullable | Fecha de finalización de la comparación |

**Relaciones:**

- **N:1 con `pdf_templates` (source)**: Múltiples comparaciones pueden usar la misma plantilla como fuente (`source_template`)
- **N:1 con `pdf_templates` (target)**: Múltiples comparaciones pueden usar la misma plantilla como objetivo (`target_template`)
- **N:1 con `users`**: Múltiples comparaciones pueden ser creadas por un usuario (`creator`)
- **1:N con `comparison_fields`**: Una comparación tiene múltiples diferencias a nivel de campo (`field_differences`)

---

### 5. Tabla: `comparison_fields`

**Propósito:** Corazón del análisis comparativo - almacena las diferencias detalladas a nivel de campo entre plantillas PDF, incluyendo cambios de contenido, posición y tipo de modificación.

**Columnas:**
| Nombre | Tipo SQL | Propiedades | Descripción |
|--------|----------|-------------|-------------|
| `id` | INTEGER | PK, Index | Identificador único de la diferencia |
| `comparison_id` | INTEGER | FK to comparisons.id, Not Null, Index | Referencia a la comparación padre |
| `field_name` | VARCHAR(255) | Not Null | Nombre del campo que cambió |
| `field_type` | VARCHAR(100) | Nullable | Tipo de campo (text, checkbox, etc.) |
| `change_type` | VARCHAR(50) | Nullable, Index | Tipo de cambio: 'added', 'removed', 'modified', 'unchanged' |
| `old_value` | TEXT | Nullable | Valor anterior del campo (si aplica) |
| `new_value` | TEXT | Nullable | Valor nuevo del campo (si aplica) |
| `position_x` | FLOAT | Nullable | Coordenada X del campo en el PDF |
| `position_y` | FLOAT | Nullable | Coordenada Y del campo en el PDF |
| `created_at` | DATETIME | Server Default: now() | Fecha de detección de la diferencia |

**Relaciones:**

- **N:1 con `comparisons`**: Múltiples diferencias de campo pertenecen a una comparación (`comparison`)

**Lógica de Negocio:**

- **`change_type`** categoriza el impacto:
  - `'added'`: Campo nuevo en la plantilla objetivo
  - `'removed'`: Campo eliminado de la plantilla fuente
  - `'modified'`: Campo existente con cambios en contenido/propiedades
  - `'unchanged'`: Campo sin cambios (para referencia)
- **Coordenadas** (`position_x`, `position_y`) permiten mapear cambios espaciales
- **Valores** (`old_value`, `new_value`) capturan cambios de contenido específicos

## Diagrama de Relaciones

```
users (1) -----> (N) pdf_templates
  |                     |
  |                     +----> (N) template_versions
  |                     |
  +----> (N) comparisons (N) <----- (1) pdf_templates (source)
              |                              |
              |                              | (target)
              +----> (N) comparison_fields   |
                                             |
                                    pdf_templates (target)
```

## Índices y Optimizaciones

**Índices Principales:**

- `users.email` (unique, para login rápido)
- `users.is_active` (para filtrar usuarios activos)
- `pdf_templates.name`, `pdf_templates.version` (búsquedas de plantillas)
- `pdf_templates.created_at` (ordenamiento temporal)
- `comparisons.status` (filtrar por estado de proceso)
- `comparisons.created_at` (histórico de comparaciones)
- `comparison_fields.change_type` (análisis por tipo de cambio)

**Claves Foráneas con Índices:**

- Todas las FK tienen índices para optimizar joins
- `template_versions.is_current` indexado para encontrar versión actual rápidamente

## Consideraciones de Diseño

1. **Versionado Flexible**: El sistema permite múltiples versiones por plantilla con marcado de versión actual
2. **Comparaciones Bidireccionales**: Las plantillas pueden ser tanto fuente como objetivo en diferentes comparaciones
3. **Análisis Granular**: `comparison_fields` permite análisis detallado hasta nivel de campo individual
4. **Trazabilidad Completa**: Timestamps y referencias de usuario en todas las operaciones principales
5. **Escalabilidad**: Diseño preparado para grandes volúmenes de plantillas y comparaciones del SEPE
