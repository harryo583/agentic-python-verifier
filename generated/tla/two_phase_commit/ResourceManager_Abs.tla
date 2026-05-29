---- MODULE ResourceManager_Abs ----
EXTENDS Naturals, FiniteSets
CONSTANTS RMs
VARIABLES rmState

States == {"working", "prepared", "committed", "aborted"}

TypeOK == rmState \in [RMs -> States]

Init == rmState = [r \in RMs |-> "working"]

Prepare(r) ==
  /\ rmState[r] = "working"
  /\ rmState' = [rmState EXCEPT ![r] = "prepared"]

VoteAbort(r) ==
  /\ rmState[r] = "working"
  /\ rmState' = [rmState EXCEPT ![r] = "aborted"]

ReceiveCommit(r) ==
  /\ rmState[r] = "prepared"
  /\ rmState' = [rmState EXCEPT ![r] = "committed"]

ReceiveAbort(r) ==
  /\ rmState[r] \in {"working", "prepared"}
  /\ rmState' = [rmState EXCEPT ![r] = "aborted"]

Next == \E r \in RMs : Prepare(r) \/ VoteAbort(r) \/ ReceiveCommit(r) \/ ReceiveAbort(r)

vars == << rmState >>
Spec == Init /\ [][Next]_vars

Inv == TypeOK
Property == Inv
====
