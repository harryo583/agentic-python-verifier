---- MODULE RM2_Abs ----
EXTENDS Naturals

CONSTANTS States

VARIABLES rm2State

vars == << rm2State >>

Init == rm2State = "working"

Prepare    == rm2State = "working"  /\ rm2State' = "prepared"
ApplyCommit == rm2State = "prepared" /\ rm2State' = "committed"
ApplyAbort  == rm2State \in {"working","prepared"} /\ rm2State' = "aborted"

Next == Prepare \/ ApplyCommit \/ ApplyAbort

Spec == Init /\ [][Next]_vars

Inv == rm2State \in States
====
