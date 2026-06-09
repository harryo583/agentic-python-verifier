---- MODULE LogStore_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS Nodes, Entries, MaxLen

VARIABLES log

vars == << log >>

BSeq == UNION { [1..k -> Entries] : k \in 0..MaxLen }

TypeOK == log \in [Nodes -> BSeq]

Init == log = [n \in Nodes |-> << >>]

AppendEntry ==
  \E n \in Nodes, e \in Entries :
    /\ Len(log[n]) < MaxLen
    /\ log' = [log EXCEPT ![n] = Append(log[n], e)]

Replicate ==
  \E src \in Nodes, dst \in Nodes :
    /\ src # dst
    /\ log' = [log EXCEPT ![dst] = log[src]]

Next == AppendEntry \/ Replicate
Spec == Init /\ [][Next]_vars

Inv == TypeOK
====
