---- MODULE LogStore_Impl ----
EXTENDS Naturals, Sequences

CONSTANTS Nodes, Entries, MaxLen

(* --algorithm LogStore
variables
  log = [n \in Nodes |-> << >>];
begin
  Loop:
    while TRUE do
      either
        with n \in Nodes, e \in Entries do
          await Len(log[n]) < MaxLen;
          log := [log EXCEPT ![n] = Append(log[n], e)];
        end with;
      or
        with src \in Nodes, dst \in Nodes do
          await src # dst;
          log := [log EXCEPT ![dst] = log[src]];
        end with;
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "ad280d3a" /\ chksum(tla) = "72fa43e1")
VARIABLES log, pc

vars == << log, pc >>

Init == (* Global variables *)
        /\ log = [n \in Nodes |-> << >>]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \/ /\ \E n \in Nodes:
                   \E e \in Entries:
                     /\ Len(log[n]) < MaxLen
                     /\ log' = [log EXCEPT ![n] = Append(log[n], e)]
           \/ /\ \E src \in Nodes:
                   \E dst \in Nodes:
                     /\ src # dst
                     /\ log' = [log EXCEPT ![dst] = log[src]]
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ log' = log

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

BSeq == UNION { [1..k -> Entries] : k \in 0..MaxLen }

TypeOK ==
  /\ log \in [Nodes -> BSeq]
  /\ pc \in {"Loop", "Finish", "Done"}

Inv == TypeOK

Property == TypeOK
====
