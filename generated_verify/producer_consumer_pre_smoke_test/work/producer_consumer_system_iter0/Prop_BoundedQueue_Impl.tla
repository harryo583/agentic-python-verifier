---- MODULE Prop_BoundedQueue_Impl ----
EXTENDS BoundedQueue_Impl

\* Enumerate Inv-states (no transitions); check Property on each.
PInit == Inv
PSpec == PInit /\ [][UNCHANGED vars]_vars

====
