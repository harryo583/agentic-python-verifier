---- MODULE ReplicatedLog ----
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Nodes, MaxLen, MaxTerm, Entries

VARIABLES role, term, logs

RLvars == << role, term, logs >>

Roles == {"leader", "follower"}
Leaders == { n \in Nodes : role[n] = "leader" }
BoundedSeqs == UNION { [1..k -> Entries] : k \in 0..MaxLen }

TypeOK ==
  /\ role \in [Nodes -> Roles]
  /\ term \in [Nodes -> 0..MaxTerm]
  /\ logs \in [Nodes -> BoundedSeqs]

Init ==
  /\ role = [n \in Nodes |-> "follower"]
  /\ term = [n \in Nodes |-> 0]
  /\ logs = [n \in Nodes |-> << >>]

ElectLeader(n) ==
  /\ Cardinality(Leaders) = 0
  /\ role' = [role EXCEPT ![n] = "leader"]
  /\ UNCHANGED << term, logs >>

StepDown(n) ==
  /\ role[n] = "leader"
  /\ role' = [role EXCEPT ![n] = "follower"]
  /\ UNCHANGED << term, logs >>

BumpTerm(n) ==
  /\ term[n] < MaxTerm
  /\ term' = [m \in Nodes |-> term[n] + 1]
  /\ UNCHANGED << role, logs >>

AppendEntry(n, e) ==
  /\ role[n] = "leader"
  /\ Len(logs[n]) < MaxLen
  /\ logs' = [logs EXCEPT ![n] = Append(logs[n], e)]
  /\ UNCHANGED << role, term >>

Replicate(f, ldr) ==
  /\ role[ldr] = "leader"
  /\ role[f] = "follower"
  /\ logs' = [logs EXCEPT ![f] = logs[ldr]]
  /\ UNCHANGED << role, term >>

Next ==
  \/ \E n \in Nodes : ElectLeader(n)
  \/ \E n \in Nodes : StepDown(n)
  \/ \E n \in Nodes : BumpTerm(n)
  \/ \E n \in Nodes, e \in Entries : AppendEntry(n, e)
  \/ \E f \in Nodes, ldr \in Nodes : Replicate(f, ldr)

Spec == Init /\ [][Next]_RLvars

ElectionSafety == Cardinality(Leaders) <= 1
LogBounds == \A n \in Nodes : Len(logs[n]) <= MaxLen /\ \A i \in 1..Len(logs[n]) : logs[n][i] \in Entries
TermBounds == \A n \in Nodes : term[n] \in 0..MaxTerm

Inv == TypeOK /\ ElectionSafety /\ LogBounds /\ TermBounds

Property == ElectionSafety /\ LogBounds /\ TermBounds
====
