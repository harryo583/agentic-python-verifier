---- MODULE Prop_BackingStore_Impl ----
EXTENDS BackingStore_Impl

\* Enumerate Inv-states (no transitions); check Property on each.
PInit == Inv
PSpec == PInit /\ [][UNCHANGED vars]_vars

====
