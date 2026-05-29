---- MODULE BoundedQueue_Impl ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity

(* --algorithm BoundedQueue
variables buffer = << >>;
begin
  Loop:
    while TRUE do
      either
        await Len(buffer) < Capacity;
        with v \in 1..10 do
          buffer := Append(buffer, v);
        end with;
      or
        await Len(buffer) > 0;
        buffer := Tail(buffer);
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "414f7efd" /\ chksum(tla) = "5476610d")
VARIABLES buffer, pc

vars == << buffer, pc >>

Init == (* Global variables *)
        /\ buffer = << >>
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \/ /\ Len(buffer) < Capacity
              /\ \E v \in 1..10:
                   buffer' = Append(buffer, v)
           \/ /\ Len(buffer) > 0
              /\ buffer' = Tail(buffer)
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED buffer

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

BoundedSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

Inv ==
  /\ buffer \in BoundedSeq(1..10, Capacity)
  /\ pc \in {"Loop", "Finish", "Done"}

Property == Len(buffer) \in 0..Capacity

====
