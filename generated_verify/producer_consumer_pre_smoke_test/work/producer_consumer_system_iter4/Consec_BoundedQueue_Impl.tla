---- MODULE Consec_BoundedQueue_Impl ----
EXTENDS BoundedQueue_Impl

\* Treat every Inv-satisfying state as initial; one step must preserve Inv.
IInit == Inv
ISpec == IInit /\ [][Next]_vars

====
