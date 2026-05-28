---- MODULE Consec_Consumer_Impl ----
EXTENDS Consumer_Impl

\* Treat every Inv-satisfying state as initial; one step must preserve Inv.
IInit == Inv
ISpec == IInit /\ [][Next]_vars

====
