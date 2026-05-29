---- MODULE LogStore_Impl ----
EXTENDS Naturals, Sequences

CONSTANTS Nodes, MaxLen, Entries

BoundedSeqs == UNION { [1..k -> Entries] : k \in 0..MaxLen }

(* --algorithm LogStore
variables
  logs = [n \in Nodes |-> << >>];
begin
  LLoop:
    while TRUE do
      either
        with n \in Nodes, e \in Entries do
          await Len(logs[n]) < MaxLen;
          logs := [logs EXCEPT ![n] = Append(logs[n], e)];
        end with;
      or
        with f \in Nodes, src \in Nodes do
          logs := [logs EXCEPT ![f] = logs[src]];
        end with;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "c34c21f3" /\ chksum(tla) = "db8de583")
VARIABLE logs

vars == << logs >>

Init == (* Global variables *)
        /\ logs = [n \in Nodes |-> << >>]

Next == \/ /\ \E n \in Nodes:
                \E e \in Entries:
                  /\ Len(logs[n]) < MaxLen
                  /\ logs' = [logs EXCEPT ![n] = Append(logs[n], e)]
        \/ /\ \E f \in Nodes:
                \E src \in Nodes:
                  logs' = [logs EXCEPT ![f] = logs[src]]

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

TypeOK == logs \in [Nodes -> BoundedSeqs]

Inv == TypeOK /\ \A n \in Nodes : Len(logs[n]) <= MaxLen
Property == \A n \in Nodes : Len(logs[n]) <= MaxLen
====
