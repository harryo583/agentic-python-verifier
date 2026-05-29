---- MODULE Prop_Producer_Impl ----
EXTENDS Producer_Impl

\* Enumerate Inv-states (no transitions); check Property on each.
PInit == Inv
PSpec == PInit /\ [][UNCHANGED vars]_vars

====
