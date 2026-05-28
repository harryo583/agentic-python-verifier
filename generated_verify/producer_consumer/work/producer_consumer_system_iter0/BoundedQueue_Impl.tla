---- MODULE BoundedQueue_Impl ----
EXTENDS Naturals, Sequences

CONSTANT Capacity

(* --algorithm BoundedQueue
variables buffer = << >>;
begin
  Loop:
    while TRUE do
      either
        with v \in 1..10 do
          await Len(buffer) < Capacity;
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
\* BEGIN TRANSLATION (chksum(pcal) = "5f5cb211" /\ chksum(tla) = "647db2cf")
VARIABLES buffer, pc

vars == << buffer, pc >>

Init == (* Global variables *)
        /\ buffer = << >>
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \/ /\ \E v \in 1..10:
                   /\ Len(buffer) < Capacity
                   /\ buffer' = Append(buffer, v)
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

Inv ==
  /\ Len(buffer) \in 0..Capacity
  /\ \A i \in 1..Len(buffer) : buffer[i] \in 1..10
  /\ pc \in {"Loop", "Finish", "Done"}

Property == Len(buffer) \in 0..Capacity

====
