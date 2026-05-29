---- MODULE Election_Abs ----
EXTENDS Naturals, FiniteSets

CONSTANTS Nodes, MaxTerm

VARIABLES role, term
vars == << role, term >>

Roles == {"leader", "follower"}
Leaders == { n \in Nodes : role[n] = "leader" }

TypeOK ==
  /\ role \in [Nodes -> Roles]
  /\ term \in [Nodes -> 0..MaxTerm]

Init ==
  /\ role = [n \in Nodes |-> "follower"]
  /\ term = [n \in Nodes |-> 0]

ElectLeader(n) ==
  /\ Cardinality(Leaders) = 0
  /\ role' = [role EXCEPT ![n] = "leader"]
  /\ UNCHANGED term

StepDown(n) ==
  /\ role[n] = "leader"
  /\ role' = [role EXCEPT ![n] = "follower"]
  /\ UNCHANGED term

BumpTerm(n) ==
  /\ term[n] < MaxTerm
  /\ term' = [m \in Nodes |-> term[n] + 1]
  /\ UNCHANGED role

Next ==
  \/ \E n \in Nodes : ElectLeader(n)
  \/ \E n \in Nodes : StepDown(n)
  \/ \E n \in Nodes : BumpTerm(n)

Spec == Init /\ [][Next]_vars

Inv == TypeOK /\ Cardinality(Leaders) <= 1
Property == Cardinality(Leaders) <= 1
====
