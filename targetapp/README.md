# PLUMBLINE

The application Handrail is tested against: a mock core-banking product run by two fictional
credit unions, Quarrybrook (`:8081`) and Fernhollow (`:8082`), from the same code with different
frame names, field names, button labels and screen headers.

It is deliberately hostile in the ways real back-office software is: framesets, table layouts,
no element ids, no test hooks, no label associations, a per-render form token, and terse
mainframe messages. A test endpoint arms faults on the server (`/__test__/arm_fault`,
`/__test__/reset`) so timeouts, maintenance pages and dialogs can be demonstrated on demand.

```bash
make up      # both tenants
make down
```

Sign on as `dcolewell` / `plumbline-demo` (supervisor) or `mrivas` (teller). Members 400118,
400226, 400337, 400445; share `400226-S0002` is already on hold.

Handrail itself never imports this package. The tests do.
