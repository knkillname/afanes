---
type: project
status: active
due_date: "{{ date:+10d }}"
---

# Book the car service

The service light came on, and the garage down the road handles this model.

- [x] Note the mileage before the visit <!-- {actual: "{{ date:-2d }}"} -->
- [ ] Book a slot at [The corner garage](<note:The corner garage>) <!-- {plan: "{{ date:+3d }}"} -->
- [ ] Check the tyre pressure before leaving
