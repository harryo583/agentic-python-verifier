---- MODULE ResourceManager_Abs ----
EXTENDS Naturals

VARIABLES rmState

States == {"working","prepared","committed","aborted"}

Init == rmState = "working"

Prepare       == rmState = "working"  /\ rmState' = "prepared"
ReceiveCommit == rmState = "prepared" /\ rmState' = "committed"
ReceiveAbort  == rmState \in {"working","prepared"} /\ rmState' = "aborted"
Stutter       == rmState' = rmState

Next == Prepare \/ ReceiveCommit \/ ReceiveAbort \/ Stutter

vars == << rmState >>
Spec == Init /\ [][Next]_vars

Inv == rmState \in States
====
