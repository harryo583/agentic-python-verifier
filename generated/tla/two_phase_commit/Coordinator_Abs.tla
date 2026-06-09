---- MODULE Coordinator_Abs ----
EXTENDS Naturals, FiniteSets

CONSTANTS RMIDs, Decisions

VARIABLES votes, decision

vars == << votes, decision >>

Init == votes = {} /\ decision = "none"

ReceivePrepared(r) ==
  /\ decision = "none"
  /\ r \in RMIDs
  /\ votes' = votes \cup {r}
  /\ UNCHANGED decision

DecideCommit ==
  /\ decision = "none"
  /\ votes = RMIDs
  /\ decision' = "commit"
  /\ UNCHANGED votes

DecideAbort ==
  /\ decision = "none"
  /\ decision' = "abort"
  /\ UNCHANGED votes

Next == (\E r \in RMIDs : ReceivePrepared(r)) \/ DecideCommit \/ DecideAbort

Spec == Init /\ [][Next]_vars

Inv ==
  /\ votes \in SUBSET RMIDs
  /\ decision \in Decisions
  /\ (decision = "commit") => (votes = RMIDs)
====
