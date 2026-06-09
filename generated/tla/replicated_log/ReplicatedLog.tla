---- MODULE ReplicatedLog ----
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Nodes, Entries, MaxLen, MaxTerm

VARIABLES role, term, log, pcE, pcL

E == INSTANCE Election_Impl WITH role <- role, term <- term, pc <- pcE
L == INSTANCE LogStore_Impl WITH log <- log, pc <- pcL

vars == << role, term, log, pcE, pcL >>

BSeq == UNION { [1..k -> Entries] : k \in 0..MaxLen }

Init == E!Init /\ L!Init
Next == (E!Next /\ UNCHANGED << log, pcL >>) \/ (L!Next /\ UNCHANGED << role, term, pcE >>)
Spec == Init /\ [][Next]_vars

Leaders == { n \in Nodes : role[n] = "leader" }
AtMostOneLeader == Cardinality(Leaders) <= 1

TypeOK ==
  /\ role \in [Nodes -> {"leader", "follower"}]
  /\ term \in [Nodes -> 0..MaxTerm]
  /\ log \in [Nodes -> BSeq]
  /\ pcE \in {"Loop", "Finish", "Done"}
  /\ pcL \in {"Loop", "Finish", "Done"}

Inv == TypeOK /\ AtMostOneLeader

Property == AtMostOneLeader /\ TypeOK
====
