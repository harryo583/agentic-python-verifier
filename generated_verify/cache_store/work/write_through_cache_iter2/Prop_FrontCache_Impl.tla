---- MODULE Prop_FrontCache_Impl ----
EXTENDS FrontCache_Impl

\* Enumerate Inv-states (no transitions); check Property on each.
PInit == Inv
PSpec == PInit /\ [][UNCHANGED vars]_vars

====
