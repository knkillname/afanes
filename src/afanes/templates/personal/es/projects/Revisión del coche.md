---
type: project
status: active
due_date: "{{ date:+10d }}"
---

# Reserva la revisión del coche

La luz de revisión se encendió, y el taller de la calle trabaja con este modelo.

- [x] Anotar el kilometraje antes de la visita <!-- {actual: "{{ date:-2d }}"} -->
- [ ] Reservar una cita en [El taller del barrio](<note:El taller del barrio>) <!-- {plan: "{{ date:+3d }}"} -->
- [ ] Comprobar la presión de los neumáticos antes de salir
