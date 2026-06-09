---- MODULE RM1_Abs ----
EXTENDS Naturals

CONSTANTS States

VARIABLES rm1State

vars == << rm1State >>

Init == rm1State = "working"

Prepare    == rm1State = "working"  /\ rm1State' = "prepared"
ApplyCommit == rm1State = "prepared" /\ rm1State' = "committed"
ApplyAbort  == rm1State \in {"working","prepared"} /\ rm1State' = "aborted"

Next == Prepare \/ ApplyCommit \/ ApplyAbort

Spec == Init /\ [][Next]_vars

Inv == rm1State \in States
====
