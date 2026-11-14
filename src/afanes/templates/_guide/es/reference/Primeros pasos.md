---
type: reference
---

# Primeros pasos

Afanes lee y escribe una carpeta de archivos Markdown llamada bóveda. Cada archivo es una nota. El
primer bloque entre líneas `---` contiene los metadatos que usa Afanes; el resto del archivo es
Markdown corriente. Nada se guarda en otro lugar, así que los archivos siguen siendo legibles y
portables sin la aplicación.

## Cuatro tipos de notas

- **Nota** — una idea que aún no se ha aclarado. Las capturas viven en `inbox/`, y una nota solo
  puede estar allí.
- **Referencia** — algo que merece conservarse y sobre lo que no se actúa: un contacto, un lugar, un
  tema, un proceso. Las referencias viven en `reference/`, opcionalmente dentro de una carpeta de
  categoría.
- **Proyecto** — un resultado que necesita más de una acción. Los proyectos viven en `projects/`, y
  los pasos que los hacen avanzar son elementos de casilla en el mismo archivo.
- **Registro** — una entrada de diario con fecha. Su fecha es su identidad y vive bajo `log/`.

## Etiquetas de categoría

Una referencia puede declarar una clave `category`. La etiqueta es libre: agrupa las referencias bajo
un encabezado en el explorador y les da una carpeta dentro de `reference/`. `person`, `place`,
`team`, `process`, `topic` y `source` son convenciones, no una lista fija; escribe cualquier etiqueta
que ayude a encontrar la nota de nuevo.

## Tarjetas de plantilla de referencia

Cada bóveda nueva incluye una carpeta `templates/` con tarjetas de plantilla de referencia y de
registro. Una tarjeta de referencia declara una `category` y un cuerpo inicial; una tarjeta de
registro declara `type: log` y un cuerpo inicial. Elegir una tarjeta al procesar, en el explorador o
en el Registro crea una nota con la forma correcta. Las tarjetas iniciales cubren una persona, un
equipo, una organización, un lugar, un proceso, un tema, una fuente y una entrada diaria.

La carpeta no forma parte de las notas. Los archivos de `templates/` quedan fuera del explorador y de
las búsquedas, y sus nombres nunca chocan con los nombres de las notas. Edita, añade o elimina
tarjetas con cualquier editor de texto; una tarjeta eliminada de la carpeta sigue eliminada.

## Entradas de registro

Una entrada de registro es una página de diario. Su `date` es su identidad y su nombre de archivo:
`2025.md`, `2025-10.md` o `2025-10-12.md`, archivado bajo `log/<año>/` o `log/<año>/<mes>/`. Solo
puede existir una entrada de registro para cada fecha exacta. El primer encabezado es el título
visible, así que el nombre del archivo sigue siendo una fecha.

Abre la sección **Registro** para ver el calendario y el árbol de años contraído. **Entrada de hoy**
abre la página de hoy en modo lectura, o un borrador sin guardar cuando el día está libre; un día
vacío del calendario o el signo más de una fila de mes o año vacía abre el mismo borrador para esa
fecha. Un control **Inicial** en el borrador ofrece las tarjetas de registro hasta que el cuerpo tiene
contenido. **Entradas** muestra solo notas de registro; **Todo** es una lente de fechas sobre toda la
bóveda. Cambiar la fecha de una entrada la renombra y la mueve, actualiza los enlaces `log:`
entrantes y reescribe el encabezado solo mientras siga siendo igual al título de fecha generado
anterior.

## Cómo una captura se convierte en proyecto

1. Escribe una línea en la bandeja de entrada. La primera línea se convierte en el nombre y el título
   de la nota.
2. Abre la captura y elige **Procesar**. Elige un resultado: Papelera, Más tarde, Referencia,
   Proyecto, Entrada de registro, Añadir paso o Hacer ahora.
3. Un resultado de Proyecto pide un estado y una fecha de vencimiento opcionales. La captura se mueve
   a `projects/` y su cuerpo se convierte en el cuerpo del proyecto.
4. Abre el proyecto y añade pasos como `- [ ] Redactar la lista`. El primer paso sin marcar en el
   orden del documento es el próximo paso del proyecto.

## Nombres y enlaces

El nombre del archivo sin extensión es la identidad de la nota. Renombrar el archivo renombra la nota,
y otras notas llegan a ella por ese nombre. El título visible viene del primer encabezado de nivel 1
del cuerpo, así que un nombre de archivo y un encabezado pueden diferir.

Enlaza a una referencia o captura con `[Etiqueta](<note:Nombre>)`, a un proyecto con
`[Etiqueta](<project:Nombre>)` o a una entrada de registro con `[Etiqueta](<log:2025-10-12>)`. Usa
corchetes angulares cuando el nombre contenga espacios para que el destino no sea ambiguo.

## Trabajar a mano

Aquí nada está oculto. Edita cualquier nota con un editor de texto; Afanes vuelve a indexar la carpeta
al abrirla. Mueve una nota a `trash/` para dejar de verla. Esta guía es una referencia corriente:
renómbrala, edítala o muévela a `trash/` cuando ya no la necesites.
