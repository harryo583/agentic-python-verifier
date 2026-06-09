---- MODULE Election_Abs ----
EXTENDS Naturals, FiniteSets

CONSTANTS Nodes, MaxTerm

VARIABLES role, term

vars == << role, term >>

TypeOK ==
  /\ role \in [Nodes -> {"leader", "follower"}]
  /\ term \in [Nodes -> 0..MaxTerm]

Leaders == { n \in Nodes : role[n] = "leader" }
AtMostOneLeader == Cardinality(Leaders) <= 1

Init ==
  /\ \E ldr \in Nodes :
       role = [n \in Nodes |-> IF n = ldr THEN "leader" ELSE "follower"]
  /\ term = [n \in Nodes |-> 0]

ElectLeader ==
  /\ \E ldr \in Nodes :
       LET maxT == CHOOSE m \in {term[n] : n \in Nodes} :
                    \A n \in Nodes : term[n] <= m
       IN /\ maxT < MaxTerm
          /\ role' = [n \in Nodes |-> IF n = ldr THEN "leader" ELSE "follower"]
          /\ term' = [n \in Nodes |-> maxT + 1]

StepDown == UNCHANGED vars

Next == ElectLeader \/ StepDown
Spec == Init /\ [][Next]_vars

Inv == TypeOK /\ AtMostOneLeader
====
