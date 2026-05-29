---- MODULE Coordinator_Abs ----
EXTENDS Naturals, FiniteSets
CONSTANTS RMs
VARIABLES coordState, votes, decision

CoordStates == {"init", "preparing", "decided"}
VoteVals == {"none", "prepared", "aborted"}
Decisions == {"none", "Commit", "Abort"}

TypeOK ==
  /\ coordState \in CoordStates
  /\ votes \in [RMs -> VoteVals]
  /\ decision \in Decisions

Init ==
  /\ coordState = "init"
  /\ votes = [r \in RMs |-> "none"]
  /\ decision = "none"

SendPrepare ==
  /\ coordState = "init"
  /\ coordState' = "preparing"
  /\ UNCHANGED << votes, decision >>

CollectVote(r, v) ==
  /\ coordState = "preparing"
  /\ votes[r] = "none"
  /\ v \in {"prepared", "aborted"}
  /\ votes' = [votes EXCEPT ![r] = v]
  /\ UNCHANGED << coordState, decision >>

DecideCommit ==
  /\ coordState = "preparing"
  /\ decision = "none"
  /\ \A r \in RMs : votes[r] = "prepared"
  /\ decision' = "Commit"
  /\ coordState' = "decided"
  /\ UNCHANGED votes

DecideAbort ==
  /\ coordState = "preparing"
  /\ decision = "none"
  /\ (\E r \in RMs : votes[r] = "aborted")
  /\ decision' = "Abort"
  /\ coordState' = "decided"
  /\ UNCHANGED votes

Next == SendPrepare \/ (\E r \in RMs, v \in {"prepared","aborted"} : CollectVote(r, v)) \/ DecideCommit \/ DecideAbort

vars == << coordState, votes, decision >>
Spec == Init /\ [][Next]_vars

Inv ==
  /\ TypeOK
  /\ (decision = "Commit") => (\A r \in RMs : votes[r] = "prepared")
Property == Inv
====
