---- MODULE LogStore_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS Nodes, MaxLen, Entries

VARIABLES logs
vars == << logs >>

BoundedSeqs == UNION { [1..k -> Entries] : k \in 0..MaxLen }

TypeOK == logs \in [Nodes -> BoundedSeqs]

Init == logs = [n \in Nodes |-> << >>]

AppendEntry(n, e) ==
  /\ Len(logs[n]) < MaxLen
  /\ e \in Entries
  /\ logs' = [logs EXCEPT ![n] = Append(logs[n], e)]

Replicate(f, src) ==
  /\ logs' = [logs EXCEPT ![f] = logs[src]]

Next ==
  \/ \E n \in Nodes, e \in Entries : AppendEntry(n, e)
  \/ \E f \in Nodes, src \in Nodes : Replicate(f, src)

Spec == Init /\ [][Next]_vars

Inv == TypeOK /\ \A n \in Nodes : Len(logs[n]) <= MaxLen
Property == \A n \in Nodes : Len(logs[n]) <= MaxLen
====
