---- MODULE Consec_BackingStore_Impl ----
EXTENDS BackingStore_Impl

\* Treat every Inv-satisfying state as initial; one step must preserve Inv.
IInit == Inv
ISpec == IInit /\ [][Next]_vars

====
