---- MODULE Prop_Cache_Impl ----
EXTENDS Cache_Impl

\* Enumerate Inv-states (no transitions); check Property on each.
PInit == InvImpl
PSpec == PInit /\ [][UNCHANGED vars]_vars

====
