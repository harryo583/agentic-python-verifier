---- MODULE BoundedQueue_Impl ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxLen

BSeq(S) == UNION { [1..n -> S] : n \in 0..MaxLen }

(* --algorithm BoundedQueue {
  variables buffer = << >>;
  {
    Loop:
      while (Len(buffer) < MaxLen) {
        either {
          await Len(buffer) < Capacity;
          with (v \in 1..10) {
            buffer := Append(buffer, v);
          }
        } or {
          await Len(buffer) > 0;
          buffer := Tail(buffer);
        }
      }
  }
} *)
\* BEGIN TRANSLATION (chksum(pcal) = "3290e0a2" /\ chksum(tla) = "5d76c176")
VARIABLES buffer, pc

vars == << buffer, pc >>

Init == (* Global variables *)
        /\ buffer = << >>
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ IF Len(buffer) < MaxLen
              THEN /\ \/ /\ Len(buffer) < Capacity
                         /\ \E v \in 1..10:
                              buffer' = Append(buffer, v)
                      \/ /\ Len(buffer) > 0
                         /\ buffer' = Tail(buffer)
                   /\ pc' = "Loop"
              ELSE /\ pc' = "Done"
                   /\ UNCHANGED buffer

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ buffer \in BSeq(1..10)
  /\ Len(buffer) \in 0..Capacity
  /\ pc \in {"Loop", "Done"}

Property == Len(buffer) \in 0..Capacity

====
