---- MODULE TwoPhaseCommit ----
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS RMs

VARIABLES rmState, coordState, votes, decision, pcRM, pcCo

RM == INSTANCE ResourceManager_Impl WITH rmState <- rmState, pc <- pcRM
CO == INSTANCE Coordinator_Impl WITH coordState <- coordState, votes <- votes, decision <- decision, pc <- pcCo

vars == << rmState, coordState, votes, decision, pcRM, pcCo >>

Init == RM!Init /\ CO!Init
Next == (RM!Next /\ UNCHANGED << coordState, votes, decision, pcCo >>)
        \/ (CO!Next /\ UNCHANGED << rmState, pcRM >>)
Spec == Init /\ [][Next]_vars

States == {"working", "prepared", "committed", "aborted"}
Terminal(s) == s \in {"committed", "aborted"}

Agreement ==
  \A r1, r2 \in RMs :
    (Terminal(rmState[r1]) /\ Terminal(rmState[r2])) => rmState[r1] = rmState[r2]

CommittedImpliesDecision ==
  (\E r \in RMs : rmState[r] = "committed") => (decision = "Commit")

Inv ==
  /\ RM!Inv
  /\ CO!Inv
  /\ Agreement
  /\ CommittedImpliesDecision

Property == Agreement /\ CommittedImpliesDecision

====
