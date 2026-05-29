---- MODULE Prop_Consumer_Impl ----
EXTENDS Consumer_Impl

\* Enumerate Inv-states (no transitions); check Property on each.
PInit == Inv
PSpec == PInit /\ [][UNCHANGED vars]_vars

====
