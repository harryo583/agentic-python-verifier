---- MODULE Consec_Cache_Impl ----
EXTENDS Cache_Impl

\* Treat every Inv-satisfying state as initial; one step must preserve Inv.
IInit == InvImpl
ISpec == IInit /\ [][Next]_vars

====
