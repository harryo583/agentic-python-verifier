---- MODULE TwoPhaseCommit ----
EXTENDS Naturals, FiniteSets, Sequences, TLC

RMIDs == {"rm1", "rm2"}
States == {"working", "prepared", "committed", "aborted"}
Decisions == {"none", "commit", "abort"}

VARIABLES rm1State, rm2State, votes, decision, pcRM1, pcRM2, pcCo

RM1 == INSTANCE RM1_Impl WITH States <- States, rm1State <- rm1State, pc <- pcRM1
RM2 == INSTANCE RM2_Impl WITH States <- States, rm2State <- rm2State, pc <- pcRM2
Co  == INSTANCE Coordinator_Impl WITH RMIDs <- RMIDs, Decisions <- Decisions, votes <- votes, decision <- decision, pc <- pcCo

vars == << rm1State, rm2State, votes, decision, pcRM1, pcRM2, pcCo >>

Init ==
  /\ RM1!Init
  /\ RM2!Init
  /\ Co!Init

Next ==
  \/ (RM1!Next /\ UNCHANGED << rm2State, votes, decision, pcRM2, pcCo >>)
  \/ (RM2!Next /\ UNCHANGED << rm1State, votes, decision, pcRM1, pcCo >>)
  \/ (Co!Next  /\ UNCHANGED << rm1State, rm2State, pcRM1, pcRM2 >>)

Spec == Init /\ [][Next]_vars

Agreement ==
  ~ ( (rm1State = "committed" /\ rm2State = "aborted")
   \/ (rm1State = "aborted"   /\ rm2State = "committed") )

CommitImpliesDecision ==
  (rm1State = "committed" \/ rm2State = "committed") => (decision = "commit")

Inv ==
  /\ rm1State \in States
  /\ rm2State \in States
  /\ decision \in Decisions
  /\ votes \in SUBSET RMIDs
  /\ pcRM1 \in {"RMLoop", "Finish", "Done"}
  /\ pcRM2 \in {"RMLoop", "Finish", "Done"}
  /\ pcCo  \in {"CoLoop", "Finish", "Done"}
  /\ (decision = "commit") => (votes = RMIDs)
  /\ (rm1State = "committed") => (decision = "commit")
  /\ (rm2State = "committed") => (decision = "commit")
  /\ Agreement

Property == Agreement /\ CommitImpliesDecision
====
